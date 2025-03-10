import hashlib
import json
import platform
import re
import toml
import json
from tqdm.auto import tqdm
import logging
import os,requests
from dataclasses import dataclass
from typing import Any, Union, cast
from datetime import datetime
from swebench.harness.repo_arch import GithubApiPool, get_cargo_test_cmd, get_repo_arch
from swebench.harness.make_test_cmds import make_test_cmds
from swebench.harness.constants import (
    SWEbenchInstance,
    KEY_INSTANCE_ID,
    FAIL_TO_PASS,
    PASS_TO_PASS,
    MAP_REPO_TO_INSTALL,
    MAP_REPO_TO_REQS_PATHS,
    MAP_REPO_VERSION_TO_SPECS,
    USE_X86,
    SWE_BENCH_URL_RAW,
    NON_OSDK_CRATES,
    OSDK_CRATES
)
from swebench.harness.dockerfiles import (
    get_dockerfile_base,
    get_dockerfile_env,
    get_dockerfile_instance,
    get_dockerfile_env_asterinas,
)
from swebench.harness.utils import (
    get_test_directives,
)

logger = logging.getLogger(__name__)

DIFF_MODIFIED_FILE_REGEX = r"--- a/(.*)"

default_config = {
        "rustc": "1.81.0",
        "pre_install": [
            "git submodule update --init --recursive",
        ],
    }
#todo
threshold_time = "2024-11-27"

RUST_RELEASE_DATES = [
    ("2015-05-15", "1.0.0"),
    ("2015-06-25", "1.1.0"),
    ("2015-08-07", "1.2.0"),
    ("2015-09-17", "1.3.0"),
    ("2015-10-29", "1.4.0"),
    ("2015-12-10", "1.5.0"),
    ("2016-01-21", "1.6.0"),
    ("2016-03-03", "1.7.0"),
    ("2016-04-14", "1.8.0"),
    ("2016-05-26", "1.9.0"),
    ("2016-07-07", "1.10.0"),
    ("2016-08-18", "1.11.0"),
    ("2016-09-29", "1.12.0"),
    ("2016-10-20", "1.12.1"),
    ("2016-11-10", "1.13.0"),
    ("2016-12-22", "1.14.0"),
    ("2017-02-02", "1.15.0"),
    ("2017-02-09", "1.15.1"),
    ("2017-03-16", "1.16.0"),
    ("2017-04-27", "1.17.0"),
    ("2017-06-08", "1.18.0"),
    ("2017-07-20", "1.19.0"),
    ("2017-08-31", "1.20.0"),
    ("2017-10-12", "1.21.0"),
    ("2017-11-22", "1.22.0"),
    ("2017-11-22", "1.22.1"),
    ("2018-01-04", "1.23.0"),
    ("2018-02-15", "1.24.0"),
    ("2018-03-01", "1.24.1"),
    ("2018-03-29", "1.25.0"),
    ("2018-05-10", "1.26.0"),
    ("2018-05-29", "1.26.1"),
    ("2018-06-05", "1.26.2"),
    ("2018-06-21", "1.27.0"),
    ("2018-07-10", "1.27.1"),
    ("2018-07-20", "1.27.2"),
    ("2018-08-02", "1.28.0"),
    ("2018-09-13", "1.29.0"),
    ("2018-09-25", "1.29.1"),
    ("2018-10-11", "1.29.2"),
    ("2018-10-25", "1.30.0"),
    ("2018-11-08", "1.30.1"),
    ("2018-12-06", "1.31.0"),
    ("2018-12-20", "1.31.1"),
    ("2019-01-17", "1.32.0"),
    ("2019-02-28", "1.33.0"),
    ("2019-04-11", "1.34.0"),
    ("2019-04-25", "1.34.1"),
    ("2019-05-14", "1.34.2"),
    ("2019-05-23", "1.35.0"),
    ("2019-07-04", "1.36.0"),
    ("2019-08-15", "1.37.0"),
    ("2019-09-20", "1.38.0"),
    ("2019-11-07", "1.39.0"),
    ("2019-12-19", "1.40.0"),
    ("2020-01-30", "1.41.0"),
    ("2020-02-27", "1.41.1"),
    ("2020-03-12", "1.42.0"),
    ("2020-04-23", "1.43.0"),
    ("2020-05-07", "1.43.1"),
    ("2020-06-04", "1.44.0"),
    ("2020-06-18", "1.44.1"),
    ("2020-07-16", "1.45.0"),
    ("2020-07-30", "1.45.1"),
    ("2020-08-03", "1.45.2"),
    ("2020-08-27", "1.46.0"),
    ("2020-10-08", "1.47.0"),
    ("2020-11-19", "1.48.0"),
    ("2020-12-31", "1.49.0"),
    ("2021-02-11", "1.50.0"),
    ("2021-03-25", "1.51.0"),
]

RUST_RELEASE_DATES.extend([
    ("2021-05-06", "1.52.0"),
    ("2021-06-17", "1.53.0"),
    ("2021-07-29", "1.54.0"),
    ("2021-09-09", "1.55.0"),
    ("2021-10-21", "1.56.0"),
    ("2021-12-02", "1.57.0"),
    ("2022-01-13", "1.58.0"),
    ("2022-02-24", "1.59.0"),
    ("2022-04-07", "1.60.0"),
    ("2022-05-19", "1.61.0"),
    ("2022-06-30", "1.62.0"),
    ("2022-08-11", "1.63.0"),
    ("2022-09-22", "1.64.0"),
    ("2022-11-03", "1.65.0"),
    ("2022-12-15", "1.66.0"),
    ("2023-01-26", "1.67.0"),
    ("2023-03-09", "1.68.0"),
    ("2023-04-20", "1.69.0"),
    ("2023-06-01", "1.70.0"),
    ("2023-07-13", "1.71.0"),
    ("2023-08-24", "1.72.0"),
    ("2023-10-05", "1.73.0"),
    ("2023-11-16", "1.74.0"),
    ("2023-12-28", "1.75.0"),
    ("2024-02-08", "1.76.0"),
])

RUST_RELEASE_DATES.extend([
    ("2024-02-08", "1.76.0"),
    ("2024-03-21", "1.77.0"),
    ("2024-03-28", "1.77.1"),
    ("2024-03-30", "1.77.2"),
    ("2024-05-02", "1.78.0"),
    ("2024-06-13", "1.79.0"),
    ("2024-07-25", "1.80.0"),
    ("2024-08-08", "1.80.1"),
    ("2024-09-05", "1.81.0"),
    ("2024-10-17", "1.82.0"),
    ("2024-11-28", "1.83.0"),
    ("2025-01-09", "1.84.0"),
    ("2025-01-30", "1.84.1"),
    ("2025-02-20", "1.85.0"),
])

def get_rust_version_for_date(target_date: str) -> str:
    """
    根据给定日期返回应该使用的 Rust 版本
    参数 target_date 格式为 'YYYY-MM-DD'
    """
    target_datetime = datetime.strptime(target_date, "%Y-%m-%d")
    
    # 初始化为默认版本 1.81.0（最新版本）
    selected_version = "1.81.0"
    
    # 按照日期从最新到最旧排序版本列表
    sorted_releases = sorted(RUST_RELEASE_DATES, key=lambda x: datetime.strptime(x[0], "%Y-%m-%d"), reverse=True)
    
    # 找到第一个不晚于目标日期的版本
    for release_date, version in sorted_releases:
        release_datetime = datetime.strptime(release_date, "%Y-%m-%d")
        if release_datetime <= target_datetime:
            selected_version = version
            break
            
    return selected_version

@dataclass
class TestSpec:
    """
    A dataclass that represents a test specification for a single instance of SWE-bench.
    """
    instance_id: str
    repo: str
    version: str
    repo_script_list: list[str]
    eval_script_list: list[str]
    env_script_list: list[str]
    arch: str
    cargo_toml: str
    FAIL_TO_PASS: list[str]
    PASS_TO_PASS: list[str]
    tests_changed: list[str]
    image_tag: str

    @property
    def setup_env_script(self):
        return "\n".join(["#!/bin/bash", "set -euxo pipefail"] + self.env_script_list) + "\n"

    @property
    def eval_script(self):
        return "\n".join(["#!/bin/bash", "set -uxo pipefail"] + self.eval_script_list) + "\n"
        # Don't exit early because we need to revert tests at the end

    @property
    def install_repo_script(self):
        return "\n".join(["#!/bin/bash", "set -euxo pipefail"] + self.repo_script_list) + "\n"

    @property
    def base_image_key(self):
        if self.repo == "asterinas/asterinas":
            if self.version =="0.1" or self.version == '0.2':
                return f"jinuxdev/jinux:{self.image_tag}"
            return f"asterinas/asterinas:{self.image_tag}"
        return f"sweb.base.{self.arch}:latest"

    @property
    def env_image_key(self):
        """
        The key for the environment image is based on the hash of the environment script list.
        If the environment script list changes, the image will be rebuilt automatically.

        Note that old images are not automatically deleted, so consider cleaning up old images periodically.
        """
        hash_object = hashlib.sha256()
        hash_object.update(str(self.env_script_list).encode("utf-8"))
        hash_value = hash_object.hexdigest()
        val = hash_value[:22]  # 22 characters is still very likely to be unique
        return f"sweb.env.{self.arch}.{val}.{self.repo.replace('/','_').lower()}.{self.version.replace('.','_')}:latest"

    @property
    def instance_image_key(self):
        return f"sweb.eval.{self.arch}.{self.instance_id.lower()}:latest"

    def get_instance_container_name(self, run_id=None):
        if not run_id:
            return f"sweb.eval.{self.instance_id}"
        return f"sweb.eval.{self.instance_id}.{run_id}"

    @property
    def base_dockerfile(self):
        return get_dockerfile_base(self.platform, self.arch)

    @property
    def env_dockerfile(self):
        if self.repo == "asterinas/asterinas":
            return get_dockerfile_env_asterinas(self.platform, tag=self.image_tag)
        return get_dockerfile_env(self.platform, self.arch)

    @property
    def instance_dockerfile(self):
        return get_dockerfile_instance(self.platform, self.env_image_key)

    @property
    def platform(self):
        if self.arch == "x86_64":
            return "linux/x86_64"
        elif self.arch == "arm64":
            return "linux/arm64/v8"
        else:
            raise ValueError(f"Invalid architecture: {self.arch}")


def get_test_specs_from_dataset(dataset: Union[list[SWEbenchInstance], list[TestSpec]]) -> list[TestSpec]:
    """
    Idempotent function that converts a list of SWEbenchInstance objects to a list of TestSpec objects.
    """
    if isinstance(dataset[0], TestSpec):
        return cast(list[TestSpec], dataset)
    typed_dataset = cast(list[SWEbenchInstance], dataset)
    progress_bar = tqdm(typed_dataset, desc="Converting instances to test specs")
    mapped_results = map(make_test_spec, progress_bar)
    filtered_result = [item for item in mapped_results if item is not None]
    return filtered_result


def make_repo_script_list(specs, repo, repo_directory, base_commit, env_name,time):
    """
    Create a list of bash commands to set up the repository for testing.
    This is the setup script for the instance image.
    """
    setup_commands = [
        "pwd",
        # f"git clone -o origin https://github.com/{repo} {repo_directory}",
        # f"chmod -R 777 {repo_directory}",  # So nonroot user can run tests
        f"cd {repo_directory}",
        f"git reset --hard {base_commit}",
    ]
    rust_version = get_rust_version_for_date(time)
    setup_commands.append(f"rustup default {rust_version}")
    setup_commands.append(f"cargo lts {time}")
    setup_commands.append(f"cargo update")

    if repo in MAP_REPO_TO_INSTALL:
        setup_commands.append(MAP_REPO_TO_INSTALL[repo])

    # Run pre-install set up if provided
    if "pre_install" in specs:
        for pre_install in specs["pre_install"]:
            setup_commands.append(pre_install)

    if "install" in specs:
        setup_commands.append(specs["install"])
    return setup_commands


def make_env_script_list(instance, specs, repo, repo_directory, env_name):
    """
    Creates the list of commands to set up the conda environment for testing.
    This is the setup script for the environment image.
    """
    HEREDOC_DELIMITER = "EOF_59812759871"
    if repo == "asterinas/asterinas":
        env_setup_commands = specs.get("env_setup", [])  # 如果没有 "env_setup"，则返回空列表 []
        reqs_commands = [
        "pwd",
        "ls -la .",
        # "curl google.com",
        f"git clone -o origin https://github.com/{repo} {repo_directory}",
        f"chmod -R 777 {repo_directory}",  # So nonroot user can run tests
        f"cd {repo_directory}",
        f"git reset --hard {instance['environment_setup_commit']}",
        *env_setup_commands,
        f"make build",
        # f"git reset --hard {instance['environment_setup_commit']}"
        ]
    else:
        env_setup_commands = specs.get("env_setup", [])  # 如果没有 "env_setup"，则返回空列表 []
        reqs_commands = [
            f"MAX_RETRIES=5",
            f"""
            retry() {{
                local attempt=0
                local command="$*"
                until $command; do
                    attempt=$((attempt + 1))
                    if [ $attempt -ge $MAX_RETRIES ]; then
                        echo "Command '$command' failed after $MAX_RETRIES attempts. Exiting."
                        exit 1
                    fi
                    echo "Command '$command' failed. Retrying... (Attempt $attempt/$MAX_RETRIES)"
                done
            }}
            """,
            f"retry rustup default {specs['rustc']}",
            f"retry git clone -o origin https://github.com/{repo} {repo_directory}",
            f"chmod -R 777 {repo_directory}",  # So nonroot user can run tests
            f"cd {repo_directory}",
            f"git reset --hard {instance['environment_setup_commit']}",
            *env_setup_commands,
            f"retry cargo fetch",
        ]

    return reqs_commands


def make_eval_script_list(instance, specs, env_name, repo_directory, base_commit, test_patch, tests_changed):
    """
    Applies the test patch and runs the tests.
    """
    HEREDOC_DELIMITER = "EOF_114329324912"
    test_files = re.findall(DIFF_MODIFIED_FILE_REGEX, test_patch)
    # Reset test files to the state they should be in before the patch.
    reset_tests_command = f"git checkout {base_commit} {' '.join(test_files)}"
    if instance["instance_id"] == "asterinas__asterinas-1138":
        reset_tests_command = f"git checkout {base_commit} {' '.join(test_files)} && rm -rf /testbed/osdk/my-first-os"
    apply_test_patch_command = (
        f"git apply -v - <<'{HEREDOC_DELIMITER}'\n{test_patch}\n{HEREDOC_DELIMITER}"
    )
    diff_cmd = "git diff"
    git_status_cmd = "git status"

    test_commands = make_test_cmds(instance, specs, env_name, repo_directory, base_commit, test_patch, tests_changed)
    if test_commands is None:
        pool = GithubApiPool(tokens=os.environ["GITHUB_TOKENS"])
        repo = get_repo_arch(pool, instance['repo'].split("/")[0], instance['repo'].split("/")[1], base_commit)
        test_commands = get_cargo_test_cmd(repo, tests_changed)

    # write test commands
    test_commands_output_dir = os.path.join(os.path.dirname(__file__),'save','test_commands',instance['repo'].replace('/','__'))
    os.makedirs(test_commands_output_dir,exist_ok=True)
    test_commands_output_path = os.path.join(test_commands_output_dir,f"{instance['instance_id']}.json")
    if not os.path.exists(test_commands_output_path):
        with open(test_commands_output_path,'w',encoding='utf-8') as f:
            json.dump(test_commands,f)


    eval_commands = []
    if "eval_commands" in specs:
        eval_commands += specs["eval_commands"]
    eval_commands += [
        f"git config --global --add safe.directory {repo_directory}",  # for nonroot user
        f"cd {repo_directory}",
    ]
    if "install" in specs:
        eval_commands.append(specs["install"])
    eval_commands += [
        # reset_tests_command,
        apply_test_patch_command,
        git_status_cmd,
        diff_cmd,
        *(test_commands),
        git_status_cmd,
        reset_tests_command
    ]
    return eval_commands


def make_test_spec(instance: SWEbenchInstance) -> TestSpec | None:
    if isinstance(instance, TestSpec):
        return instance
    if "version" not in instance or instance["version"] is None:
        logger.warning(f"Instance {instance['instance_id']} does not have a version field, skipping")
        return None
    instance_id = instance[KEY_INSTANCE_ID]
    repo = instance["repo"]
    version = instance["version"]
    base_commit = instance["base_commit"]
    problem_statement = instance["problem_statement"]
    hints_text = instance["hints_text"]  # Unused
    time = instance["created_at"].split("T")[0] 

    test_patch = instance["test_patch"]
    def _from_json_or_obj(key: str) -> Any:
        """If key points to string, load with json"""
        if isinstance(instance[key], str):
            return json.loads(instance[key])
        return instance[key]

    pass_to_pass = _from_json_or_obj(PASS_TO_PASS)
    fail_to_pass = _from_json_or_obj(FAIL_TO_PASS)

    env_name = "testbed"
    repo_directory = f"/{env_name}"
    specs = MAP_REPO_VERSION_TO_SPECS.get(repo, {}).get(version, default_config)

    repo_script_list = make_repo_script_list(specs, repo, repo_directory, base_commit, env_name,time)
    try:
        env_script_list = make_env_script_list(instance, specs, repo, repo_directory, env_name)
    except Exception as e:
        logger.warning(f"Failed to create make env script for {instance_id}: {e}")
        return None

    if platform.machine() in {"aarch64", "arm64"}:
        # use arm64 unless explicitly specified
        arch = "arm64" if instance_id not in USE_X86 else "x86_64"
    else:
        arch = "x86_64"

    # get cargo.toml
    # req_path = MAP_REPO_TO_REQS_PATHS[repo]
    # reqs_url = os.path.join(SWE_BENCH_URL_RAW, repo, base_commit, req_path)
    # reqs = requests.get(reqs_url)
    # cargo_toml = reqs.text
    cargo_toml = ""
    tests_changed = list(dict.fromkeys(get_test_directives(instance)))
    image_tag = MAP_REPO_VERSION_TO_SPECS.get(repo, {}).get(version, {}).get("image_tag", None)
    # get eval script list
    eval_script_list = make_eval_script_list(
        instance, specs, env_name, repo_directory, base_commit, test_patch, tests_changed
    )

    return TestSpec(
        instance_id=instance_id,
        repo=repo,
        env_script_list=env_script_list,
        repo_script_list=repo_script_list,
        eval_script_list=eval_script_list,
        version=version,
        arch=arch,
        tests_changed=tests_changed,
        cargo_toml=cargo_toml,
        FAIL_TO_PASS=fail_to_pass,
        PASS_TO_PASS=pass_to_pass,
        image_tag=image_tag,
    )
