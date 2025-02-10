import argparse
import os
import sys
import json
import re
from datasets import load_dataset
from pathlib import Path
from tqdm import tqdm
import pandas as pd
import subprocess
import openai
import requests
import base64
GITHUB_API_URL = "https://api.github.com"

def extract_function_content_in_range(file_content, start_line, target_line):
    """
    提取文件内容中包含给定行号区间的函数的代码内容。

    :param file_content: Rust 源文件内容（字符串）
    :param start_line: 区间的起始行号
    :param target_line: 区间的结束行号
    :return: 包含这些行号的函数名及其代码内容
    """
    lines = file_content.splitlines()
    functions = []
    stack = []
    current_function = None
    current_function_lines = []

    # 修改后的正则表达式匹配函数定义
    fn_pattern = re.compile(
        r'^\s*'                               # 行首的空白字符
        r'(?:pub(?:\([^)]+\))?\s+)?'          # 可选的可见性修饰符
        r'(?:const\s+)?'                      # 可选的 const 关键字
        r'(?:async\s+)?'                      # 可选的 async 关键字
        r'(?:unsafe\s+)?'                     # 可选的 unsafe 关键字
        r'fn\s+'                              # fn 关键字
        r'(\w+)'                              # 函数名，捕获组
        r'(?:<[^>]*>\s*)?'                    # 可选的泛型参数列表
        r'\('                                 # 左括号
    )

    # 遍历文件行
    for i, line in enumerate(lines, start=1):
        # 检查是否是函数定义
        match = fn_pattern.match(line)
        if match:
            if current_function:
                # 结束当前函数并记录范围
                functions.append((current_function[0], current_function[1], current_function_lines))
            # 开始新的函数
            current_function = (match.group(1), i)
            current_function_lines = [line]
            # 重置堆栈
            stack = []
            # 检查行中是否有左花括号
            if '{' in line:
                stack.append('{')
        elif current_function:
            current_function_lines.append(line)
            # 检查是否进入新的块
            if '{' in line:
                stack.append('{')
            # 检查是否离开块
            if '}' in line:
                if stack:
                    stack.pop()
                # 如果函数块结束，记录范围
                if not stack:
                    functions.append((current_function[0], current_function[1], current_function_lines))
                    current_function = None
                    current_function_lines = []
        else:
            continue

    # 处理文件末尾未闭合的函数
    if current_function:
        functions.append((current_function[0], current_function[1], current_function_lines))

    # 查找所有包含目标行号区间的函数并返回函数体
    result_functions = {}
    for fn_name, start, fn_lines in functions:
        end = start + len(fn_lines) - 1
        # 判断函数是否包含指定的行号范围
        if not (end < start_line or start > target_line):
            result_functions[fn_name] = '\n'.join(fn_lines)
    return result_functions


def get_pull_request(repo_owner, repo_name, pr_number, access_token=None):
    url = f"{GITHUB_API_URL}/repos/{repo_owner}/{repo_name}/pulls/{pr_number}"
    headers = {"Accept": "application/vnd.github.v3+json"}
    access_token = access_token or os.getenv("GITHUB_TOKEN")
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        # print(f"PR fetched: {response.json()}")
        return response.json()  # 返回 PR 的详细信息
    else:
        print(f"Failed to fetch PR: {response.status_code} - {response.json()}")
        return None

def get_file_content(repo, commit, file_path, access_token=None):
    access_token = access_token or os.getenv("GITHUB_TOKEN")
    url = f"{GITHUB_API_URL}/repos/{repo}/contents/{file_path}?ref={commit}"
    headers = {"Accept": "application/vnd.github.v3+json"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"

    # 获取文件内容
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to fetch file: {response.status_code} - {response.json()}")
        return None

    # 解码文件内容 (Base64 编码)
    file_data = response.json()
    file_content = base64.b64decode(file_data["content"]).decode("utf-8")
    return file_content

def get_function_code(file_content, location):
    """
    获取指定仓库某个提交中某文件的函数代码。

    :param repo: str, 仓库名称 (格式: owner/repo_name)
    :param commit: str, 提交哈希值或分支名称
    :param file_path: str, 文件的路径
    :param location: tuple, 函数所在的起始行和结束行 (start_line, end_line)
    :param access_token: str, GitHub 的个人访问令牌（可选）
    :return: str, 函数的代码
    """
    # 构建 GitHub API 请求 URL

    # 提取函数代码
    # start_line, end_line = location
    # file_lines = file_content.splitlines()
    # function_code = "\n".join(file_lines[start_line - 1:end_line])  # 注意行号从 1 开始
    function_code = extract_function_content_in_range(file_content, location[0], location[1])

    return function_code


def extract_file_paths_and_locations(patch_text):
    """
    解析 unidiff 格式的 patch, 提取旧文件的文件路径和被修改的行号。

    返回旧文件路径列表和对应文件的修改行号字典。
    """
    file_paths = []
    locations = {}
    current_file = None
    
    for line in patch_text.splitlines():
        if line.startswith('--- '):
            # 原文件路径
            original_file = line[6:].strip()
            current_file = original_file
            if current_file.endswith('.rs'):
                file_paths.append(current_file)
                locations[current_file] = []
        elif line.startswith('@@ '):
            # hunks，提取旧文件的行号范围
            match = re.match(r'@@ -(\d+)(?:,(\d+))? \+\d+(?:,\d+)? @@', line)
            if match:
                start_line = int(match.group(1))
                line_count = int(match.group(2)) if match.group(2) else 1
                location = (start_line, start_line + line_count)
                if current_file in locations:
                    locations[current_file].append(location)
    return file_paths, locations


def get_branch_from_commit(instance):
    """
    使用 git 命令获取指定 commit 所在的分支名称。
    """
    REPO_OWNER = instance["repo"].split("/")[0]
    REPO_NAME = instance["repo"].split("/")[1]
    PR_NUMBER = instance["pull_number"]
    pr_data = get_pull_request(REPO_OWNER, REPO_NAME, PR_NUMBER)
    if pr_data:
        source_branch = pr_data.get('head', {}).get('ref', "unknown")
    return source_branch

def stringify_locations(locations):
    """
    将文件路径和行号范围字典转换为清晰的字符串表示。

    :param locations: 字典，文件路径为键，行号范围列表为值。
    :return: 格式化的字符串
    """
    result = []
    for file_path, ranges in locations.items():
        result.append(f"File: {file_path}")
        for start, end in ranges:
            result.append(f"  Line Range: {start}-{end}")
        result.append("")  # 空行分隔文件
    return "\n".join(result)

def main():
    # 配置 argparse
    parser = argparse.ArgumentParser(description="Convert HF dataset to JSON format.")
    parser.add_argument('--dataset_name', type=str, default="r1v3r/auto_0207_bug", help='Hugging Face dataset name')
    parser.add_argument('--split', type=str, default="train", help='Dataset split to use')
    parser.add_argument('--output', type=str, default="entries.json", help='Output JSON file path')
    args = parser.parse_args()
    
    # 加载数据集
    print(f"Loading dataset '{args.dataset_name}' split '{args.split}' from Hugging Face...")
    try:
        dataset = load_dataset(args.dataset_name, split=args.split)
    except Exception as e:
        print(f"Error loading dataset: {e}")
        sys.exit(1)
    
    entries = []
    
    print("Classifying problem statements...")
    for example in tqdm(dataset, desc="Classifying"):
        problem_statement = example.get('problem_statement', None)
        instance_id = example.get('instance_id', None)
        repo = example.get('repo', "unknown")
        base_commit = example.get('base_commit', "unknown")
        patch = example.get('patch', "")
        
        if pd.isna(problem_statement) or not problem_statement:
            classification = 'Unknown'
        else:
            # problem_type, severity_level, reason = classify_with_openai(problem_statement, openai_api_key)
            
            # 解析 patch，提取 file_path 和 location
            file_paths, locations = extract_file_paths_and_locations(patch)
            # 获取分支名称
            branch = get_branch_from_commit(example)

            code_snippets = ""
            locations_string = ""
            for file_path, location_list in locations.items():
                print(f"Processing file: {file_path}")
                file_content = get_file_content(repo, base_commit, file_path)
                locations_string += f"{file_path}: "
                for location in location_list:
                    locations_string += f"line: {location[0]}-{location[1]}, "
                    function_code_dict = get_function_code(file_content, location)
                    print(f"Function code: {function_code_dict}")
                    # 合并所有函数代码
                    for fn_name, fn_code in function_code_dict.items():
                        code_snippets += fn_code + '\n'
            
            # 构建条目
            entry = {
                "instance_id": instance_id,
                "code_snippet": code_snippets,  # 需根据实际需求填充
                "target_function": code_snippets,  # 需根据实际需求填充
                "review_type": "function",  # 固定值
                "repo": repo,
                "issue_detail":{
                    "location": locations_string,
                    "description": problem_statement
                },
                "branch": branch,
                "file_path": ",".join(file_paths),
                "language": "rust"  # 固定值
            }
            
            entries.append(entry)
            print(entry)
    
    # 保存分类为 'Feature Development' 的条目到 JSON 文件
    output_json_path = args.output
    print(f"Saving Feature Development entries to {output_json_path}...")
    try:
        with open(output_json_path, 'w', encoding='utf-8') as json_file:
            json.dump(entries, json_file, ensure_ascii=False, indent=4)
        print("转换完成，结果已保存。")
    except Exception as e:
        print(f"Error saving JSON file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
