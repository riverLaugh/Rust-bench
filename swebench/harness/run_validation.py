from __future__ import annotations
import time

import docker
import json
import resource
import traceback
import sys
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from tqdm import tqdm
import os
import json

from swebench.harness.constants import (
    APPLY_PATCH_FAIL,
    APPLY_PATCH_PASS,
    INSTANCE_IMAGE_BUILD_DIR,
    KEY_INSTANCE_ID,
    # RUN_EVALUATION_LOG_DIR,
)
from swebench.harness.docker_utils import (
    remove_image,
    copy_to_container,
    exec_run_with_timeout,
    cleanup_container,
    list_images,
    should_remove,
    clean_images,
)
from swebench.harness.docker_build import (
    BuildImageError,
    build_container,
    build_env_images,
    close_logger,
    setup_logger,
)
from swebench.harness.grading import get_eval_report
from swebench.harness.test_spec import make_nightly_test_spec, make_test_spec, TestSpec
from swebench.harness.utils import load_swebench_dataset, str2bool
from swebench.harness.grading import get_logs_eval   
from swebench.harness.run_evaluation import get_gold_predictions, EvaluationError, get_dataset_from_preds

RUN_EVALUATION_LOG_DIR = Path("logs/run_validation")

def run_instance(
        test_spec: TestSpec,
        pred: dict,
        rm_image: bool,
        force_rebuild: bool,
        client: docker.DockerClient,
        run_id: str,
        timeout: int | None = None,
        auto: bool = False,
    ):
    """
    Run a single instance with the given prediction.

    Args:
        test_spec (TestSpec): TestSpec instance
        pred (dict): Prediction w/ model_name_or_path, model_patch, instance_id
        rm_image (bool): Whether to remove the image after running
        force_rebuild (bool): Whether to force rebuild the image
        client (docker.DockerClient): Docker client
        run_id (str): Run ID
        timeout (int): Timeout for running tests

    Returns:

    """ 
    # Set up logging directory
    instance_id = test_spec.instance_id
    model_name_or_path = pred.get("model_name_or_path", "None").replace("/", "__")
    version_dir = f"{test_spec.repo.replace('/','_')}.{test_spec.version.replace('.','_')}"
    if auto:
        log_dir = RUN_EVALUATION_LOG_DIR / "auto" /run_id / model_name_or_path / version_dir / instance_id
    else:
        log_dir = RUN_EVALUATION_LOG_DIR / run_id  / model_name_or_path/ version_dir  / instance_id
    log_dir.mkdir(parents=True, exist_ok=True)

    # Link the image build dir in the log dir
    build_dir = INSTANCE_IMAGE_BUILD_DIR / test_spec.instance_image_key.replace(":", "__")
    image_build_link = log_dir / "image_build_dir"
    if not image_build_link.exists():
        try:
            # link the image build dir in the log dir
            image_build_link.symlink_to(build_dir.absolute(), target_is_directory=True)
        except:
            # some error, idk why
            pass
    log_file = log_dir / "run_instance.log"

    # Set up report file + logger
    report_path = log_dir / "report.json"
    if report_path.exists():
        return instance_id, json.loads(report_path.read_text())
    logger = setup_logger(instance_id, log_file)

    #store cargo.toml
    cargo_toml_path = Path(log_dir / "Cargo.toml")
    cargo_toml_path.write_text(test_spec.cargo_toml)

    tests_changed = Path(log_dir / "tests_changed.txt")
    # 将数组写入文件，每个元素写入一行
    tests_changed.write_text("\n".join(test_spec.tests_changed))


    # Run the instance
    container = None
    try:
        # if test_spec.version is None:
        #     raise EvaluationError(
        #         instance_id,
        #         "No version found for instance",
        #         logger,
        #     )
        # Build + start instance container (instance image should already be built)
        container = build_container(test_spec, client, run_id, logger, rm_image, force_rebuild)
        container.start()
        logger.info(f"Container for {instance_id} started: {container.id}")
        
        # Run eval script before patch, write output to logs
        eval_file = Path(log_dir / "eval.sh")
        eval_file.write_text(test_spec.eval_script)
        copy_to_container(container, eval_file, Path("/eval.sh"))
        test_output, timed_out, total_runtime = exec_run_with_timeout(container, "/bin/bash /eval.sh", timeout)
        test_output_before_patch_path = log_dir / "test_output_before_patch.txt"
        logger.info(f'Test runtime: {total_runtime:_.2f} seconds')
        with open(test_output_before_patch_path, "w") as f:
            f.write(test_output)
            logger.info(f"Test output before patch for {instance_id} written to {test_output_before_patch_path}")
            if timed_out:
                f.write(f"\n\nTimeout error: {timeout} seconds exceeded.")
                raise EvaluationError(
                    instance_id,
                    f"Test timed out after {timeout} seconds.",
                    logger,
                )
        
        # Copy model prediction as patch file to container
        patch_file = Path(log_dir / "patch.diff")
        patch_file.write_text(pred["model_patch"] or "")
        logger.info(
            f"Intermediate patch for {instance_id} written to {patch_file}, now applying to container..."
        )
        copy_to_container(container, patch_file, Path("/tmp/patch.diff"))

        # Attempt to apply patch to container
        val = container.exec_run(
            "git apply --allow-empty -v /tmp/patch.diff",
            workdir="/testbed",
            user="root",
        )
        if val.exit_code != 0:
            logger.info(f"Failed to apply patch to container, trying again...")
            
            # try "patch --batch --fuzz=5 -p1 -i {patch_path}" to try again
            val = container.exec_run(
                "patch --batch --fuzz=5 -p1 -i /tmp/patch.diff",
                workdir="/testbed",
                user="root",
            )
            if val.exit_code != 0:
                logger.info(f"{APPLY_PATCH_FAIL}:\n{val.output.decode('utf-8')}")
                raise EvaluationError(
                    instance_id,
                    f"{APPLY_PATCH_FAIL}:\n{val.output.decode('utf-8')}",
                    logger,
                )
            else:
                logger.info(f"{APPLY_PATCH_PASS}:\n{val.output.decode('utf-8')}")
        else:
            logger.info(f"{APPLY_PATCH_PASS}:\n{val.output.decode('utf-8')}")

        # Get git diff before running eval script
        git_diff_output_before = (
            container.exec_run("git diff", workdir="/testbed").output.decode("utf-8").strip()
        )
        logger.info(f"Git diff before:\n{git_diff_output_before}")

        # Run eval script, write output to logs
        test_output, timed_out, total_runtime = exec_run_with_timeout(container, "/bin/bash /eval.sh", timeout)
        test_output_path = log_dir / "test_output.txt"
        logger.info(f'Test runtime: {total_runtime:_.2f} seconds')
        with open(test_output_path, "w") as f:
            f.write(test_output)
            logger.info(f"Test output for {instance_id} written to {test_output_path}")
            if timed_out:
                f.write(f"\n\nTimeout error: {timeout} seconds exceeded.")
                raise EvaluationError(
                    instance_id,
                    f"Test timed out after {timeout} seconds.",
                    logger,
                )
        
        # Get git diff after running eval script
        git_diff_output_after = (
            container.exec_run("git diff", workdir="/testbed").output.decode("utf-8").strip()
        )

        # Check if git diff changed after running eval script, avoid test patch overlap the patch
        logger.info(f"Git diff after:\n{git_diff_output_after}")
        if git_diff_output_after != git_diff_output_before:
            logger.info(f"Git diff changed after running eval script")

        report_map = {
            "instance_id": test_spec.instance_id,
            "FAIL_TO_PASS": [],
            "PASS_TO_PASS": [],
            "FAIL_TO_FAIL": [],
            "PASS_TO_FAIL": [],
        }
        eval_sm, found = get_logs_eval(log_file, test_output_path)
        eval_sm_ref, found_ref = get_logs_eval(log_file, test_output_before_patch_path)
        if not found:
            raise EvaluationError(
                instance_id,
                "No evaluation logs found",
                logger,
            )
        if not found_ref:
            raise EvaluationError(
                instance_id,
                "No reference evaluation logs found",
                logger,
            )
        for test, status in eval_sm.items():
            if status == "PASSED" and eval_sm_ref.get(test, None) == "FAILED":
                report_map["FAIL_TO_PASS"].append(test)
            elif status == "PASSED" and eval_sm_ref.get(test, None) == "PASSED":
                report_map["PASS_TO_PASS"].append(test)
            elif status == "FAILED" and eval_sm_ref.get(test, None) == "FAILED":
                report_map["FAIL_TO_FAIL"].append(test)
            elif status == "FAILED" and eval_sm_ref.get(test, None) == "PASSED":
                report_map["PASS_TO_FAIL"].append(test)
        
        
        if len(report_map["FAIL_TO_PASS"]) == 0 and len(report_map["PASS_TO_PASS"]) == 0 and "error[E0554]" in test_output: 
            return False,report_map
            

        return True,report_map
    except EvaluationError as e:
        error_msg = traceback.format_exc()
        logger.info(error_msg)
        print(e)
    except BuildImageError as e:
        error_msg = traceback.format_exc()
        logger.info(error_msg)
        print(e)
    except Exception as e:
        error_msg = (f"Error in evaluating model for {instance_id}: {e}\n"
                     f"{traceback.format_exc()}\n"
                     f"Check ({logger.log_file}) for more information.")
        logger.error(error_msg)
        print(e)
    finally:
        # Remove instance container + image, close logger
        cleanup_container(client, container, logger)
        if rm_image:
            remove_image(client, test_spec.instance_image_key, logger)
        close_logger(logger)
    return


def run_instances(
        predictions: dict,
        instances: list,
        cache_level: str,
        clean: bool,
        force_rebuild: bool,
        max_workers: int,
        run_id: str,
        timeout: int,
        auto: bool,
    ):
    """
    Run all instances for the given predictions in parallel.

    Args:
        predictions (dict): Predictions dict generated by the model
        instances (list): List of instances
        cache_level (str): Cache level
        clean (bool): Clean images above cache level
        force_rebuild (bool): Force rebuild images
        max_workers (int): Maximum number of workers
        run_id (str): Run ID
        timeout (int): Timeout for running tests
    """
    client = docker.from_env()
    test_specs = list(map(make_test_spec, instances))
    test_specs = [test_spec for test_spec in test_specs if test_spec is not None]

    # print number of existing instance images
    instance_image_ids = {x.instance_image_key for x in test_specs}
    existing_images = {
        tag for image in client.images.list(all=True)
        for tag in image.tags
    }
    reusable_images = instance_image_ids.intersection(existing_images)
    if not force_rebuild and reusable_images:
        print(f"Found {len(existing_images)} existing instance images. Will reuse them.")
    nightly_instance_ids = []
    # run instances in parallel
    print(f"Running {len(instances)} instances...")
    with tqdm(total=len(instances), smoothing=0, desc="Running instances") as pbar:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Create a future for running each instance
            futures = {
                executor.submit(
                    run_instance,
                    test_spec,
                    predictions[test_spec.instance_id],
                    should_remove(
                        test_spec.instance_image_key,
                        cache_level,
                        clean,
                        reusable_images,
                    ),
                    force_rebuild,
                    client,
                    run_id,
                    timeout,
                    auto,
                ): None
                for test_spec in test_specs
            }
            results = {}
            # Wait for each future to complete
            for future in as_completed(futures):
                pbar.update(1)
                try:
                    # Update progress bar, check if instance ran successfully
                    stable,res = future.result()
                    if stable is False:
                        nightly_instance_ids.append(res['instance_id'])
                    if res:
                        instance_id = res['instance_id']
                        del res['instance_id']
                        results[instance_id] = res
                except Exception as e:
                    traceback.print_exc()
                    continue
    nightly_instance = [x for x in instances if x['instance_id'] in nightly_instance_ids]
    if nightly_instance:
        nightly_test_specs = list(map(make_nightly_test_spec, nightly_instance))
        nightly_test_specs = [test_spec for test_spec in nightly_test_specs if test_spec is not None]
        print(f"Running {len(nightly_instance)} nightly instances...")
        with tqdm(total=len(nightly_instance), smoothing=0, desc="Running nightly instances") as pbar:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Create a future for running each instance
                futures = {
                    executor.submit(
                        run_instance,
                        test_spec,
                        predictions[test_spec.instance_id],
                        should_remove(
                            test_spec.instance_image_key,
                            cache_level,
                            clean,
                            reusable_images,
                        ),
                        force_rebuild,
                        client,
                        run_id,
                        timeout,
                        auto,
                    ): None
                    for test_spec in nightly_test_specs
                }
                # Wait for each future to complete
                for future in as_completed(futures):
                    pbar.update(1)
                    try:
                        # Update progress bar, check if instance ran successfully
                        stable,res = future.result()
                        if stable is False:
                            print(f"Nightly instance {res['instance_id']} failed.")
                        if res:
                            instance_id = res['instance_id']
                            del res['instance_id']
                            results[instance_id] = res
                    except Exception as e:
                        traceback.print_exc()
                        continue
    print("All instances run.")
    return results


def main(
        dataset_name: str,
        split: str,
        instance_ids: list,
        max_workers: int,
        force_rebuild: bool,
        cache_level: str,
        clean: bool,
        open_file_limit: int,
        run_id: str,
        timeout: int,
        auto: bool,
    ):
    """
    Run evaluation harness for the given dataset and predictions.
    """
    # set open file limit
    assert len(run_id) > 0, "Run ID must be provided"
    resource.setrlimit(resource.RLIMIT_NOFILE, (open_file_limit, open_file_limit))
    client = docker.from_env()

    predictions = get_gold_predictions(dataset_name, split)
    
    predictions = {pred[KEY_INSTANCE_ID]: pred for pred in predictions}

    # get dataset from predictions, list of instances
    dataset = get_dataset_from_preds(dataset_name, split, instance_ids, predictions, run_id)
    for instance in dataset:
        instance['FAIL_TO_PASS'] = []
        instance['PASS_TO_PASS'] = []
        instance['FAIL_TO_FAIL'] = []
        instance['PASS_TO_FAIL'] = []
    existing_images = list_images(client)
    print(f"Running {len(dataset)} unevaluated instances...")
    if not dataset:
        print("No instances to run.")
    else:
        # build environment images + run instances
        build_env_images(client, dataset, force_rebuild, max_workers)
        results = run_instances(predictions, dataset, cache_level, clean, force_rebuild, max_workers, run_id, timeout,auto)

    # clean images + make final report
    clean_images(client, existing_images, cache_level, clean)
    
    for instance in dataset:
        instance_id = instance["instance_id"]
        # print("instance-----------------------------------------------------------------------")
        # print(instance.keys())
        if instance_id in results:
            # merge two dictionaries, crash on duplicate keys
            # assert not any(k in instance for k in results[instance_id]), f"Duplicate keys in {instance_id}"
            instance.update(results[instance_id])

    update_json_file(dataset_name,dataset,auto)



def update_json_file(dataset_name, dataset, auto):
    # 改进后的路径生成和目录创建
    timestamp = time.strftime("%Y-%m-%d", time.localtime())
    result_path = os.path.join("./results", f"auto_{timestamp}")
    os.makedirs(result_path, exist_ok=True)
    if auto :
        dataset_name_w_results_all =  os.path.join(result_path, "defaultconfig_validated_all.json")
        dataset_name_w_results = os.path.join(result_path, "defaultconfig_validated.json")
    else:
        if dataset_name.endswith(".json") or dataset_name.endswith(".jsonl"):
            dataset_name = dataset_name.split("/")[-1]
            last_dot_idx = dataset_name.rfind(".")
            dataset_name_w_results_all = "./results/"+ dataset_name[:last_dot_idx] + "_validated.all" + dataset_name[last_dot_idx:]
            dataset_name_w_results ="./results/"+ dataset_name[:last_dot_idx] + "_validated" + dataset_name[last_dot_idx:]
        else:
            last_dot_idx = dataset_name.rfind("/")
            dataset_name_w_results_all = "./results/" + dataset_name[last_dot_idx+1:] + "_validated.all" + ".json"
            dataset_name_w_results = "./results/" + dataset_name[last_dot_idx+1:] + "_validated" + ".json"
    # Helper function to update a file with new data
    def update_file(file_path, dataset):
        # Load existing data if file exists
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                existing_data = json.load(f)
        else:
            existing_data = []

        # Create a dictionary index by instance_id for quick lookup
        instance_dict = {item["instance_id"]: item for item in existing_data}

        # Update or add new instances
        for instance in dataset:
            instance_id = instance.get("instance_id")
            if instance_id:
                instance_dict[instance_id] = instance  # Update or add new instance
            else:
                print("Warning: Missing 'instance_id' in instance:", instance)

        # Write updated data back to file
        with open(file_path, "w") as f:
            json.dump(list(instance_dict.values()), f, indent=4)

    # Update both validated and validated.all files
    update_file(dataset_name_w_results_all, dataset)

    # Only include instances with FAIL_TO_PASS for validated file
    update_file(dataset_name_w_results, [inst for inst in dataset if len(inst.get("FAIL_TO_PASS", [])) > 0])



if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--dataset_name", default="princeton-nlp/SWE-bench_Lite", type=str, help="Name of dataset or path to JSON file.")
    parser.add_argument("--split", type=str, default="train", help="Split of the dataset")
    parser.add_argument("--instance_ids", nargs="+", type=str, help="Instance IDs to run (space separated)")
    parser.add_argument("--max_workers", type=int, default=4, help="Maximum number of workers (should be <= 75%% of CPU cores)")
    parser.add_argument("--open_file_limit", type=int, default=4096, help="Open file limit")
    parser.add_argument(
        "--timeout", type=int, default=1_800, help="Timeout (in seconds) for running tests for each instance"
        )
    parser.add_argument(
        "--force_rebuild", type=str2bool, default=False, help="Force rebuild of all images"
    )
    parser.add_argument(
        "--cache_level",
        type=str,
        choices=["none", "base", "env", "instance"],
        help="Cache level - remove images above this level",
        default="env",
    )
    # if clean is true then we remove all images that are above the cache level
    # if clean is false, we only remove images above the cache level if they don't already exist
    parser.add_argument(
        "--clean", type=str2bool, default=False, help="Clean images above cache level"
    )
    parser.add_argument("--auto", type=str2bool, default=False, help="Run in auto mode")
    parser.add_argument("--run_id", type=str, required=True, help="Run ID - identifies the run")
    args = parser.parse_args()

    main(**vars(args))
