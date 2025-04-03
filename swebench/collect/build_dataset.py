#!/usr/bin/env python3

import argparse
import json
import logging
import multiprocessing
import os
from typing import Optional
from tqdm.auto import tqdm
import re

from swebench.collect.utils import (
    extract_patches,
    extract_problem_statement_and_hints,
    Repo,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_instance(repo: Repo, pull: dict , mode:str) -> dict:
    """
    Create a single task instance from a pull request, where task instance is:

    {
        repo (str): owner/repo this task instance is from,
        pull_number (int): number of PR this task instance is from,
        base_commit (str): SHA of the base commit PR is based on,
        patch (str): reference solution as .patch (apply to base commit),
        test_patch (str): test suite as .patch (apply to base commit),
    }
    """
    patch, test_patch = extract_patches(pull, repo,mode=mode)
    # patch =  extract_patches(pull,repo)
    problem_statement, hints = extract_problem_statement_and_hints(pull, repo)
    return {
        "repo": repo.repo.full_name,
        "pull_number": pull["number"],
        "instance_id": (repo.repo.full_name + "-" + str(pull["number"])).replace(
            "/", "__"
        ),
        "issue_numbers": pull["resolved_issues"],
        "base_commit": pull["base"]["sha"], #这里为什么会有问题？
        "patch": patch,
        "test_patch": test_patch,
        "problem_statement": problem_statement,
        "hints_text": hints,
        "created_at": pull["created_at"],
        "updated_at": pull["updated_at"],
    }


def is_valid_pull(pull: dict) -> bool:
    """
    Check whether PR has an associated issue and is merged

    Args:
        pull (dict): pull request object
    Returns:
        bool: whether PR is valid
    """
    if pull["merged_at"] is None:
        return False
    if "resolved_issues" not in pull or len(pull["resolved_issues"]) < 1:
        return False
    return True


def is_valid_instance(instance: dict) -> bool:
    """
    Check whether task instance has all required fields for task instance creation

    Args:
        instance (dict): task instance object
    Returns:
        bool: whether task instance is valid
    """
    if instance["patch"] is None or instance["patch"] == "":
        return False
    if instance["problem_statement"] is None or instance["problem_statement"] == "":
        return False
    return True


def has_test_patch(instance: dict) -> bool:
    """
    Check whether task instance has a test suite

    Args:
        instance (dict): task instance object
    Returns:
        bool: whether task instance has a test suite
    """
    if instance["test_patch"] is None or instance["test_patch"].strip() == "":
        return False
    return True

def extract_repo_name(file_path):
    # 使用正则表达式匹配仓库名
    match = re.search(r'/([^/]+)-task-instances\.jsonl$', file_path)
    if match:
        return match.group(1)
    else:
        return None


def main(pr_file: str, output: str, mode:str, token: Optional[str] = None, task_lock: multiprocessing.Lock = None):
    """
    Main thread for creating task instances from pull requests

    Args:
        pr_file (str): path to pull request JSONL file
        output (str): output file name
        token (str): GitHub token
    """
    if token is None:
        # Get GitHub token from environment variable if not provided
        token = os.environ.get("GITHUB_TOKEN")

    def load_repo(repo_name):
        # Return repo object for a given repo name
        owner, repo = repo_name.split("/")
        return Repo(owner, repo, token=token)


    repos = dict()
    completed = 0
    with_tests = 0
    total_instances = 0
    all_output = output + ".all"
    reponame = extract_repo_name(output)

    auto = task_lock is not None
    seen_prs = set()
    if auto:
        log = os.path.join(os.getcwd(),'logs/task_log')
        log_file = open(log, 'a')

    # Continue where we left off if output file already exists
    if os.path.exists(all_output):
        with open(all_output) as f:
            for line in f:
                pr = json.loads(line)
                if "instance_id" not in pr:
                    pr["instance_id"] = (
                        pr["repo"] + "-" + str(pr["pull_number"])
                    ).replace("/", "__")
                instance_id = pr["instance_id"]
                seen_prs.add(instance_id)
                if is_valid_instance(pr):
                    completed += 1
                    if has_test_patch(pr):
                        with_tests += 1
    logger.info(f"Will skip {len(seen_prs)} pull requests that have already been inspected")

    # Write to .all file for all PRs
    write_mode_all = "w" if not os.path.exists(all_output) else "a"

    with open(all_output, write_mode_all) as all_output:
        # Write to output file for PRs with test suites
        write_mode = "w" if not os.path.exists(output) else "a"
        with open(output, write_mode) as output:
            with open(pr_file, 'r') as file:
                total_lines = sum(1 for line in file)
            for ix, line in tqdm(enumerate(open(pr_file)), total=total_lines):
                total_instances += 1
                pull = json.loads(line)
                if ix % 100 == 0:
                    logger.info(
                        f"[{pull['base']['repo']['full_name']}] (Up to {ix} checked) "
                        f"{completed} valid, {with_tests} with tests."
                    )
                # Construct instance fields
                instance_id = (
                    pull["base"]["repo"]["full_name"] + "-" + str(pull["number"])
                )
                instance_id = instance_id.replace("/", "__")
                # skip instances which had been converted
                if instance_id in seen_prs:
                    seen_prs -= {instance_id}
                    continue
                # check if there is a related issue
                if not is_valid_pull(pull):
                    # Throw out invalid PRs
                    continue

                # Create task instance
                repo_name = pull["base"]["repo"]["full_name"]
                if repo_name not in repos:
                    repos[repo_name] = load_repo(repo_name)
                repo = repos[repo_name]
                instance = create_instance(repo, pull,mode)
                if is_valid_instance(instance):
                    # If valid, write to .all output file
                    print(
                        json.dumps(instance), end="\n", flush=True, file=all_output
                    )  # write all instances to a separate file
                    completed += 1

                    if auto:
                        # count tasks done
                        if completed % 100 == 0 & completed != 0:
                            with task_lock:
                                log_file.write( "{}: {} tasks done\n".format(reponame, completed))
                                log_file.flush()

                    if has_test_patch(instance):
                        # If has test suite, write to output file
                        print(json.dumps(instance), end="\n", flush=True, file=output)
                        with_tests += 1

    if auto:
        cur_repo_exist = False
        with open(log,'r') as f:
            for line in f:
                if line.split(":")[1] == reponame:
                    cur_repo_exist = True
        if not cur_repo_exist:            
            with task_lock:
                log_file.write('Done:{}\n'.format(reponame))
                log_file.flush()
        log_file.close()
    logger.info(f"[{', '.join(repos.keys())}] Total instances: {total_instances}, completed: {completed}, with tests: {with_tests}")
    logger.info(f"[{', '.join(repos.keys())}] Skipped {len(seen_prs)} pull requests that have already been beeninspected")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("pr_file", type=str, help="Path to pull request JSONL file")
    parser.add_argument("output", type=str, help="Output file name")
    parser.add_argument("--mode", type=str, help="Mode of operation")

    parser.add_argument("--token", type=str, help="GitHub token")
    args = parser.parse_args()
    main(**vars(args))
