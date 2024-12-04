from datasets import load_dataset
from datetime import datetime
from swebench.utils.dataset_utils import upload_to_huggingface
from datasets import load_dataset
import argparse


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
        example['created_at_parsed'] = datetime.strptime(example['created_at'], "%Y-%m-%dT%H:%M:%SZ")
        return example

    # 应用转换函数
    dataset = dataset.map(parse_created_at)

    # 创建一个字典，用于存储每个 version 对应的最新 base_commit
    version_to_latest_commit = {}

    for example in dataset:
        # print(example)
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
        version = example['version']
        if version in version_to_environment_setup_commit:
            example['environment_setup_commit'] = version_to_environment_setup_commit[version]
        else:
            example['environment_setup_commit'] = None  # 或者设置为其他默认值
        return example

    # 应用函数添加新列
    dataset = dataset.map(add_environment_setup_commit)
    dataset = dataset.remove_columns(['created_at_parsed'])
    
    upload_to_huggingface(dataset,dataset_name)
    # 查看添加新列后的列名和第一条记录
    # print("Columns after adding new column:", dataset.column_names)
    # print("First record after adding new column:", dataset[0])

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset_name", required=True, type=str, default=None, help="Path to task instances")
    args = parser.parse_args()
    main(args)