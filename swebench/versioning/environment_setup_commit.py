from pathlib import Path
from datasets import load_dataset
from datetime import datetime
from swebench.utils.dataset_utils import upload_to_huggingface
from datasets import load_dataset
from pandas import Timestamp
import argparse
import os
import requests
# def process_created_at(example):
#     example["created_at"] = convert_created_at(example["created_at"])
#     return example

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

def add_updated_at(sample):
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
    # sample = process_created_at(sample)
    return sample


def main(args):
# 加载数据集
    dataset_name = args.dataset_name

    if dataset_name.endswith('.json'):
        dataset = load_dataset("json", data_files= dataset_name)['train']
        dataset_name = dataset_name.split('/')[-1].split('.')[0]
    else:
        split = 'train'
        dataset = load_dataset(dataset_name, split=split)

    # 查看数据集的列名和第一条记录
    # 定义一个函数，将字符串转换为 datetime 对象
    def parse_created_at(example):
        if isinstance(example['created_at'], datetime):
            example['created_at_parsed'] = example['created_at']
        elif isinstance(example['created_at'], Timestamp):
            example['created_at_parsed'] = example['created_at'].to_pydatetime()
        elif isinstance(example['created_at'], str):
            example['created_at_parsed'] = datetime.strptime(example['created_at'], "%Y-%m-%dT%H:%M:%SZ")
        else:
            raise ValueError(f"Unsupported time type: {type(example['created_at'])}")
        return example

    # 应用转换函数
    dataset = dataset.map(parse_created_at)
    dataset = dataset.map(add_updated_at)
    # 创建一个字典，用于存储每个 version 对应的最新 base_commit
    version_to_latest_commit = {}

    for example in dataset:
        if 'version' not in example:
            continue
        version = example['version']
        created_at = example['created_at_parsed']
        base_commit = example['base_commit']
        
        # 如果当前 version 尚未在字典中，或者当前 example 的 created_at 比字典中记录的更新，则更新字典
        if (version not in version_to_latest_commit) or (created_at > version_to_latest_commit[version]['created_at']):
            version_to_latest_commit[version] = {
                'base_commit': base_commit,
                'created_at': created_at
            }

    # 创建一个只包含 version 到 environment_setup_commit 的映射
    version_to_environment_setup_commit = {version: info['base_commit'] for version, info in version_to_latest_commit.items()}

    # 定义一个函数，根据 version 添加 environment_setup_commit
    def add_environment_setup_commit(example):
        if 'version' not in example:
            example['environment_setup_commit'] = None
            return example
        version = example['version']
        if version in version_to_environment_setup_commit:
            example['environment_setup_commit'] = version_to_environment_setup_commit[version]
        else:
            example['environment_setup_commit'] = None  # 或者设置为其他默认值
        return example

    # 应用函数添加新列
    dataset = dataset.map(add_environment_setup_commit)
    dataset = dataset.remove_columns(['created_at_parsed'])
    if args.output_dir:
        file_name = args.dataset_name.split('/')[-1]
        file_path = Path(args.output_dir + '/' + file_name)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        print(args.output_dir)
        print(file_name)
        dataset.to_json(file_path)
        # with file_path.open('w') as f:
        #     f.write(dataset.to_json(orient='records', lines=True))
        # dataset.save_to_disk(args.output_dir)
    else:
        upload_to_huggingface(dataset,dataset_name)
    # 查看添加新列后的列名和第一条记录
    # print("Columns after adding new column:", dataset.column_names)
    # print("First record after adding new column:", dataset[0])

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset_name", required=True, type=str, default=None, help="Path to task instances")
    parser.add_argument("--output_dir", required=False, type=str, default=None, help="Path to save the output file")
    args = parser.parse_args()
    main(args)