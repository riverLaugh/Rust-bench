import re
import os
import time
import requests
from datasets import load_dataset
import datetime

def convert_created_at(time_str):
    """将时间字符串转换为 ISO 8601 标准格式（YYYY-MM-DDTHH:MM:SSZ）""" 
    converted = time_str
    if isinstance(time_str, str):
        pattern = r'(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})\.\d+Z$'
        converted = re.sub(pattern, r'\1T\2Z', time_str)
    return converted

def process_created_at(example):
    example["created_at"] = convert_created_at(example["created_at"])
    return example

def get_pr_info(owner, repo, pull_number, access_token):
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        pr_data = response.json()
        return {
            "created_at": pr_data.get("created_at"),
            "updated_at": pr_data.get("updated_at"),
            "title": pr_data.get("title"),
            "state": pr_data.get("state")
        }
    else:
        print(f"Error: {response.status_code}")
        return None

def process_sample(sample):
    owner = sample["repo"].split("/")[0]
    repo = sample["repo"].split("/")[1]
    pull_number = str(sample["pull_number"])
    access_token = os.getenv("GITHUB_TOKEN")
    
    # 获取 PR 信息
    result = get_pr_info(owner, repo, pull_number, access_token)
    if result:
        sample["updated_at"] = result["updated_at"]
    else:
        sample["updated_at"] = None  # 处理失败情况
    
    # 转换 created_at 格式（如果需要）
    sample = process_created_at(sample)
    return sample


json_path = "/home/riv3r/SWE-bench/swebench/collect/tasks/getrandom-new-task-instances.jsonl"
# 加载数据集
dataset = load_dataset("json",data_files=json_path)
# print(dataset[:5])
# 处理数据集
processed_dataset = dataset.map(process_sample)
processed_dataset['train'].to_json(json_path, lines=True)
for idx in range(5):
    sample = processed_dataset['train'][idx]
    print(f"Sample {idx+1}:")
    print(f"  Updated at: {sample['updated_at']}")
    print(f"  Created at: {sample['created_at']}")



