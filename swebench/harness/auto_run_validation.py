import os
import subprocess
import logging
import argparse
import re

# 根路径
root_path = "/home/riv3r/SWE-bench/swebench"

# 配置路径
input_folder = os.path.join(root_path, "collect/tasks/auto")
output_folder = os.path.join(root_path, "versioning/results")
version_folder = os.path.join(root_path, "versioning/auto/version")
env_commit_folder = os.path.join(root_path, "versioning/auto/env_commit")
versioning_log_folder = os.path.join(root_path, "versioning/auto/log")
dataset_folder = os.path.join(root_path, "versioning/auto/dataset")
if not os.path.exists(output_folder):
    os.makedirs(output_folder)
if not os.path.exists(version_folder):
    os.makedirs(version_folder)
if not os.path.exists(env_commit_folder):
    os.makedirs(env_commit_folder)
if not os.path.exists(versioning_log_folder):
    os.makedirs(versioning_log_folder)
if not os.path.exists(dataset_folder):
    os.makedirs(dataset_folder)

num_workers = 16  # 并行线程数量


def setup_logging(rerun):
    """
    设置日志记录方式，并根据 --rerun 参数处理日志文件的清空或追加。
    """
    log_mode = "w" if rerun else "a"  # 如果 rerun 为 True，覆盖日志文件；否则追加
    log_file = os.path.join(versioning_log_folder, 'process.log')
    log_file_detail = os.path.join(versioning_log_folder, 'process_detail.log')

    # 如果 rerun 为 False（追加模式），清空 detail_log_file
    if rerun and os.path.exists(log_file_detail):
        open(log_file_detail, 'w').close()  # 清空文件内容
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, mode=log_mode),
            logging.StreamHandler()  # 可选：同时在终端显示
        ]
    )
    return log_file, log_file_detail


def run_command_with_logging(command, description, log_file_detail):
    """
    运行命令并捕获日志
    """
    logging.info(f"Running: {description} -> {' '.join(command)}")
    with open(log_file_detail, 'a') as log:  # 始终以追加模式记录详细日志
        try:
            result = subprocess.run(
                command,
                stdout=log,
                stderr=log,
                text=True,
                check=True
            )
            return result
        except subprocess.CalledProcessError as e:
            logging.error(f"Error running {description}: {e}")
            return None


def main(args):
    print(args.rerun)
    log_file, log_file_detail = setup_logging(args.rerun)
    finish = []
    if not args.rerun:  # 如果不是重新运行，则解析已有日志中的完成任务
        processing_pattern = re.compile(r"Processing: (\S+)")
        with open(log_file, 'r', encoding='utf-8') as log:
            for line in log:
                # 检测正在处理的任务
                processing_match = processing_pattern.search(line)
                if processing_match:
                    task = processing_match.group(1)
                    finish.append(task)
    print(f"finish:{finish}")
    # 遍历文件夹，找到所有 .jsonl 文件
    for root, dirs, files in os.walk(input_folder):
        for file in files:
            print(f"file :{file}")
            if file.endswith(".jsonl") and file not in finish:
                logging.info(f"Processing: {file}")
                instances_path = os.path.join(root, file)
                base_name = os.path.splitext(file)[0]
                base_name = base_name.split(".")[0]
                version_path = version_folder + f"/{base_name}_versions.json"

                # Step 1: 运行 get_versions.py
                if not os.path.exists(version_path):
                    get_versions_command = [
                        "python", f"{root_path}/versioning/get_versions.py",
                        "--instances_path", instances_path,
                        "--retrieval_method", "github",
                        "--num_workers", str(num_workers),
                        "--output_dir", version_folder,
                        "--cleanup"
                    ]
                    run_command_with_logging(get_versions_command, f"get_versions {file}", log_file_detail)

                # Step 2: 运行 environment_setup_commit.py
                if not os.path.exists(f"{root_path}/versioning/auto/dataset/{base_name}_versions.json"):
                    environment_setup_command = [
                        "python", f"{root_path}/versioning/environment_setup_commit.py",
                        "--dataset_name", version_path,
                        "--output_dir", dataset_folder
                    ]
                    result = run_command_with_logging(environment_setup_command, f"environment_setup_commit {file}", log_file_detail)
                    if result is None:
                        os.remove(version_path)
                        continue

                # Step 3: 运行 run_validation.py
                run_validation_command = [
                    "python", "run_validation.py",
                    "--dataset_name", f"{root_path}/versioning/auto/dataset/{base_name}_versions.json",
                    "--run_id", f"{base_name}_versions",
                    "--max_workers", str(num_workers),
                    "--cache_level", "base",
                    "--auto", "True"
                ]
                run_command_with_logging(run_validation_command, f"run_validation {file}", log_file_detail)
    logging.info("All tasks completed.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--rerun', action='store_true', help="设置为 True 表示覆盖日志文件重新运行")
    args = parser.parse_args()
    main(args)
