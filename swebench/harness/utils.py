import json
import os
from pathlib import Path
import re
import requests
import tomlkit
from tomlkit import parse, dumps
from argparse import ArgumentTypeError
from datasets import Dataset, load_dataset
from dotenv import load_dotenv
from functools import cache
from typing import cast
import toml
from typing import Dict, List
from swebench.harness.constants import (
    SWEbenchInstance,
    MAP_REPO_TO_ENV_YML_PATHS,
    MAP_REPO_TO_REQS_PATHS,
    NON_TEST_EXTS,
    SWE_BENCH_URL_RAW,
    KEY_INSTANCE_ID,
    NON_OSDK_CRATES,
    OSDK_CRATES
)

load_dotenv()


def load_swebench_dataset(name="princeton-nlp/SWE-bench", split="test", instance_ids=None) -> list[SWEbenchInstance]:
    """
    Load SWE-bench dataset from Hugging Face Datasets or local .json/.jsonl file
    """
    # check that all instance IDs are in the dataset
    if instance_ids:
        instance_ids = set(instance_ids)
    # Load from local .json/.jsonl file
    if name.endswith(".json") or name.endswith(".jsonl"):
        return [
            cast(SWEbenchInstance, json.loads(instance))
            for instance in Path(name).read_text().split("\n")
            if instance
        ]

    # Load from Hugging Face Datasets
    if name.lower() in {"swe-bench", "swebench", "swe_bench"}:
        name = "princeton-nlp/SWE-bench"
    elif name.lower() in {"swe-bench-lite", "swebench-lite", "swe_bench_lite", "swe-bench_lite", "lite"}:
        name = "princeton-nlp/SWE-bench_Lite"
    dataset = cast(Dataset, load_dataset(name, split=split))
    return [cast(SWEbenchInstance, instance) for instance in dataset]


### MARK - Patch Correction
PATCH_PATTERN = re.compile(
    r"(?:diff[\w\_\.\ \/\-]+\n)?\-\-\-\s+a\/(?:.*?)\n\+\+\+\s+b\/(?:.*?)(?=diff\ |\-\-\-\ a\/|\Z)",
    re.DOTALL,
)
PATCH_FILE_PATTERN = re.compile(r"\-\-\-\s+a\/(?:.+)\n\+\+\+\s+b\/(?:.+)")
PATCH_HUNK_PATTERN = re.compile(
    r"\@\@\s+\-(\d+),(\d+)\s+\+(\d+),(\d+)\s+\@\@(.+?)(?=diff\ |\-\-\-\ a\/|\@\@\ \-|\Z)",
    re.DOTALL,
)


def get_first_idx(charlist):
    """Get index of first occurrence of "-" or "+" in charlist"""
    first_min = charlist.index("-") if "-" in charlist else len(charlist)
    first_plus = charlist.index("+") if "+" in charlist else len(charlist)
    return min(first_min, first_plus)


def get_last_idx(charlist):
    """Get index of last occurrence of "-" or "+" in charlist"""
    char_idx = get_first_idx(charlist[::-1])
    last_idx = len(charlist) - char_idx
    return last_idx + 1


def strip_content(hunk):
    """Remove trailing non +/- lines and trailing whitespace per line per hunk"""
    first_chars = list(map(lambda x: None if not len(x) else x[0], hunk.split("\n")))
    first_idx = get_first_idx(first_chars)
    last_idx = get_last_idx(first_chars)
    new_lines = list(map(lambda x: x.rstrip(), hunk.split("\n")[first_idx:last_idx]))
    new_hunk = "\n" + "\n".join(new_lines) + "\n"
    return new_hunk, first_idx - 1


def get_hunk_stats(pre_start, pre_len, post_start, post_len, hunk, total_delta):
    """Recalculate hunk start/end position and diff delta"""
    stats = {"context": 0, "added": 0, "subtracted": 0}
    hunk = hunk.split("\n", 1)[-1].strip("\n")
    for line in hunk.split("\n"):
        if line.startswith("-"):
            stats["subtracted"] += 1
        elif line.startswith("+"):
            stats["added"] += 1
        else:
            stats["context"] += 1
    context = stats["context"]
    added = stats["added"]
    subtracted = stats["subtracted"]
    pre_len = context + subtracted
    post_start = pre_start + total_delta
    post_len = context + added
    total_delta = total_delta + (post_len - pre_len)
    return pre_start, pre_len, post_start, post_len, total_delta


def extract_minimal_patch(model_patch):
    """
    Wrapper function that takes hunk and
    * Removes trailing non +/- lines and trailing whitespace per line per hunk
    * Recalculates hunk start/end position and diff delta
    * Returns new patch
    """
    model_patch = model_patch.lstrip("\n")
    new_patch = ""
    for patch in PATCH_PATTERN.findall(model_patch):
        total_delta = 0
        patch_header = PATCH_FILE_PATTERN.findall(patch)[0]
        if patch_header:
            new_patch += patch_header + "\n"
        for hunk in PATCH_HUNK_PATTERN.findall(patch):
            pre_start, pre_len, post_start, post_len, content = hunk
            pre_start, pre_len, post_start, post_len, content = list(
                map(lambda x: int(x) if x.isnumeric() else x, hunk)
            )
            content, adjust_pre_start = strip_content(content)
            pre_start += adjust_pre_start
            pre_start, pre_len, post_start, post_len, total_delta = get_hunk_stats(
                pre_start, pre_len, post_start, post_len, content, total_delta
            )
            new_patch += (
                f"@@ -{pre_start},{pre_len} +{post_start},{post_len} @@{content}"
            )
    return new_patch


def has_attribute_or_import_error(log_before):
    """
    Check to see if Attribute/Import-prefix is in log text

    Args:
        log_before (str): Validation log text before patch application
    """
    log_before = log_before.lower()

    if any([x in log_before for x in ["attribute", "import"]]):

        def get_lines_with_word(text, target_word):
            # Function to extract line(s) that contains target_word
            text, target_word = text.lower(), target_word.lower()
            lines, hits = text.split("\n")[::-1], []
            for line in lines:
                if target_word in line:
                    hits.append(line)
            return hits

        # Get line with Attribute/Import error
        lines_1 = get_lines_with_word(log_before, "attribute")
        lines_2 = get_lines_with_word(log_before, "import")
        lines_1 = " ".join(lines_1)
        lines_2 = " ".join(lines_2)

        if any([(x in lines_1 or x in lines_2) for x in ["error", "fail"]]):
            return True
    return False


@cache
def get_environment_yml_by_commit(repo: str, commit: str, env_name: str) -> str:
    for req_path in MAP_REPO_TO_ENV_YML_PATHS[repo]:
        reqs_url = os.path.join(SWE_BENCH_URL_RAW, repo, commit, req_path)
        reqs = requests.get(reqs_url)
        if reqs.status_code == 200:
            break
    else:
        raise ValueError(
            f"Could not find environment.yml at paths {MAP_REPO_TO_ENV_YML_PATHS[repo]} for repo {repo} at commit {commit}"
        )

    lines = reqs.text.split("\n")
    cleaned = []
    for line in lines:
        # Rename environment to given name
        if line.startswith("name:"):
            cleaned.append(f"name: {env_name}")
            continue
        cleaned.append(line)

    return "\n".join(cleaned)


def get_environment_yml(instance: SWEbenchInstance, env_name: str) -> str:
    """
    Get environment.yml for given task instance

    Args:
        instance (dict): SWE Bench Task instance
        env_name (str): Rename retrieved environment.yml to this name
    Returns:
        environment.yml (str): Returns environment.yml as string
    """
    # Attempt to find environment.yml at each path based on task instance's repo

    commit = (
        instance["environment_setup_commit"]
        if "environment_setup_commit" in instance
        else instance["base_commit"]
    )

    return get_environment_yml_by_commit(instance["repo"], commit, env_name)

def is_workspace_cargo_toml(f):
    """
    判断给定路径的 Cargo.toml 是否是工作区配置。

    :param cargo_toml_path: str, Cargo.toml 文件的路径
    :return: bool, 如果是工作区配置返回 True,否则返回 False
    """
    try:
        
        cargo_data = toml.load(f)
        
        workspace = cargo_data.get('workspace', {})
        members = workspace.get('members', [])
        
        return bool(workspace) and isinstance(members, list) and len(members) > 0
    except Exception as e:
        print(f"Error reading cargo.toml: {e}")
        return False


@cache
def get_requirements_by_commit(repo: str, commit: str,req_path) -> str:
    reqs_url = os.path.join(SWE_BENCH_URL_RAW, repo, commit, req_path)
    reqs = requests.get(reqs_url)
    original_cargo_toml = reqs.text
    return original_cargo_toml




def clean_cargo_toml(cargo_toml_content):
    """
    清理 Cargo.toml 内容，删除指定的部分，只保留 cargo fetch 需要的部分。
    确保相同的依赖项生成相同的输出字符串（去除注释、排序键值等）。

    :param cargo_toml_content: str, 原始 Cargo.toml 内容
    :return: str, 清理后的 Cargo.toml 内容
    """
    # 解析 TOML 内容
    try:
        cargo_data = toml.loads(cargo_toml_content)
    except toml.TomlDecodeError as e:
        raise ValueError(f"无法解析 Cargo.toml 内容。错误: {e}")
    
    # 定义需要保留的部分
    sections_to_keep = ['dependencies', 'dev-dependencies', 'build-dependencies','features']

    # 定义 [package] 部分需要保留的键
    package_keys_to_keep = ['name', 'version', 'edition']

    cleaned_data = {}

    # 处理 [package] 部分
    if 'package' in cargo_data:
        package = cargo_data['package']
        cleaned_package = {}
        for key in package_keys_to_keep:
            if key in package:
                cleaned_package[key] = package[key]
        if cleaned_package:
            # 按键排序
            cleaned_package['version']='0.0.0'
            cleaned_data['package'] = dict(sorted(cleaned_package.items()))
    
    # 保留其他指定的部分
    for section in sections_to_keep:
        if section in cargo_data:
            # 按键排序
            cleaned_section = dict(sorted(cargo_data[section].items()))
            cleaned_data[section] = cleaned_section

    # 序列化回 TOML 字符串
    cleaned_cargo_toml = toml.dumps(cleaned_data)

    # 为了确保一致性，移除多余的空行和尾随空格
    cleaned_cargo_toml = '\n'.join(line.rstrip() for line in cleaned_cargo_toml.splitlines())

    return cleaned_cargo_toml

def clean_workspace_cargo_toml(cargo_toml_content: str) -> str:
    """
    清理工作区的 Cargo.toml 内容，仅保留对 cargo fetch 有用的部分。
    确保相同的依赖项生成相同的输出字符串（去除注释、排序键值等）。

    :param cargo_toml_content: str, 原始 Cargo.toml 内容
    :return: str, 清理后的 Cargo.toml 内容
    """
    try:
        cargo_data = toml.loads(cargo_toml_content)
    except toml.TomlDecodeError as e:
        raise ValueError(f"无法解析 Cargo.toml 内容。错误: {e}")

    cleaned_data = {}

    if 'workspace' in cargo_data:
        workspace = cargo_data['workspace']
        cleaned_workspace = {}

        # 定义需要保留的键
        workspace_keys_to_keep = ['members', 'exclude', 'resolver']
        for key in workspace_keys_to_keep:
            if key in workspace:
                cleaned_workspace[key] = workspace[key]

        # 处理 [workspace.dependencies] 部分（如果存在）
        if 'dependencies' in workspace:
            dependencies = workspace['dependencies']
            cleaned_dependencies = {}

            for dep_name, dep_info in dependencies.items():
                # 检查依赖项是否为字典类型（例如 path 依赖的定义格式）
                if isinstance(dep_info, dict):
                    # 复制依赖信息并将版本设置为 "0.0.0"
                    cleaned_dep_info = dep_info.copy()
                    cleaned_dep_info['version'] = "0.0.0"
                    cleaned_dependencies[dep_name] = cleaned_dep_info
                else:
                    # 如果依赖项只是一个版本号字符串，则直接设置为 "0.0.0"
                    cleaned_dependencies[dep_name] = "0.0.0"

            # 按键排序
            cleaned_workspace['dependencies'] = dict(sorted(cleaned_dependencies.items()))

        # 处理 [workspace.package] 部分（如果存在）
        if 'package' in workspace:
            workspace_package = workspace['package']
            # 定义需要保留的键
            workspace_package_keys_to_keep = [
                # 'version',
                # 'homepage',
                # 'repository',
                # 'authors',
                # 'license',
                # 'keywords',
                # 'include',
                'edition',

            ]
            cleaned_workspace_package = {}
            for key in workspace_package_keys_to_keep:
                if key in workspace_package:
                    cleaned_workspace_package[key] = workspace_package[key]
            if cleaned_workspace_package:
                # 按键排序
                cleaned_workspace['package'] = dict(sorted(cleaned_workspace_package.items()))

        if cleaned_workspace:
            # 按键排序
            cleaned_workspace = dict(sorted(cleaned_workspace.items()))
            cleaned_data['workspace'] = cleaned_workspace

    # 序列化回 TOML 字符串
    cleaned_cargo_toml = toml.dumps(cleaned_data)

    # 移除多余的空行和尾随空格，确保一致性
    cleaned_cargo_toml = '\n'.join(line.rstrip() for line in cleaned_cargo_toml.splitlines())

    return cleaned_cargo_toml


def clean_comment(cargo_toml_content):
    """
    清理 Cargo.toml 内容，删除注释部分。
    :param cargo_toml_content: str, 原始 Cargo.toml 内容
    :return: str, 清理后的 Cargo.toml 内容
    """
    cargo_data = toml.loads(cargo_toml_content)
    
    # 移除 [[bin]]、[[example]] 和 [[test]] 部分
    cargo_data.pop("bin", None)
    cargo_data.pop("example", None)
    cargo_data.pop("test", None)
    cargo_data.pop("bench", None)
    cleaned_cargo_toml = toml.dumps(cargo_data)

    # 逐行处理，删除注释
    cleaned_lines = []
    for line in cleaned_cargo_toml.split('\n'):
        # 删除行内注释
        line = line.split('#', 1)[0]
        cleaned_lines.append(line)
    # 返回处理后的内容
    return '\n'.join(cleaned_lines)



def get_requirements(instance: SWEbenchInstance, req_path) -> str:
    """
    Get requirements.txt for given task instance

    Args:
        instance (dict): task instance
    Returns:
        requirements.txt (str): Returns requirements.txt as string
    """
    # Attempt to find requirements.txt at each path based on task instance's repo
    commit = (
        instance["environment_setup_commit"]
        if "environment_setup_commit" in instance
        else instance["base_commit"]
    )

    return get_requirements_by_commit(instance["repo"], commit,req_path)


def get_test_directives(instance: SWEbenchInstance) -> list:
    """
    Get test directives from the test_patch of a task instance

    Args:
        instance (dict): task instance
    Returns:
        directives (list): List of test directives
    """
    # For seq2seq code repos, testing command is fixed
    if instance["repo"] == "swe-bench/humaneval":
        return ["test.py"]

    # Get test directives from test patch and remove non-test files
    diff_pat = r"diff --git a/.* b/(.*)"
    add_file_pat = r"^--- /dev/null\n\+\+\+ b/(.*)"
    
    test_patch = instance["test_patch"]
    directives = re.findall(diff_pat, test_patch)
    new_directives = re.findall(add_file_pat, test_patch)
    directives.extend(new_directives)
    directives = [
        d for d in directives if not any(d.endswith(ext) for ext in NON_TEST_EXTS)
    ]
    directives_transformed = []
    for d in directives:
        # 只考虑以 ".rs" 结尾的文件，并提取文件名
        if d.endswith(".rs"):
            # 提取文件名，不包括路径
            filename = d.split("/")[-1]  # 或者使用 os.path.basename(d)
            # 移除文件扩展名 ".rs"
            filename = filename[:-3]
            directives_transformed.append(d)
    directives = directives_transformed

    return directives


def get_rust_test_command(instance: "SWEbenchInstance", specs: dict) -> list:
    # 获取 fail_to_pass 列表
    fail_to_pass = specs.get("fail_to_pass", [])

    commands = []

    for test_case in fail_to_pass:
        if test_case.endwith(".rs"):
            # 如果是编译测试文件，使用 --test 参数来指定文件
            test_file = test_case.split("/")[-1].replace(".rs", "")
            commands.append(f"cargo test --test {test_file}")
        else:
            # 对于模块内测试，直接使用模块路径生成命令
            commands.append(f"cargo test {test_case}")

    # 将所有命令连接为一个字符串，用 " && " 分隔
    # final_command = " && ".join(commands)
    return commands

def findCrate(test_files:list):
    crates_found = set()
    # Iterate over each file path in test_files
    for file_path in test_files:
        # Check if any NON_OSDK_CRATE is in the file path
        for crate in NON_OSDK_CRATES:
            if crate in file_path:
                crates_found.add(crate)
        # Check if any OSDK_CRATE is in the file path
        for crate in OSDK_CRATES:
            if crate in file_path:
                crates_found.add(crate)
    return list(crates_found)


def str2bool(v):
    """
    Minor helper function to convert string to boolean
    """
    if isinstance(v, bool):
        return v
    if v.lower() in ("yes", "true", "t", "y", "1"):
        return True
    elif v.lower() in ("no", "false", "f", "n", "0"):
        return False
    else:
        raise ArgumentTypeError("Boolean value expected.")
