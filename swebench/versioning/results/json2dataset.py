from datasets import Dataset, DatasetDict
from huggingface_hub import HfApi, HfFolder, Repository
import json
import os

def json_to_dataset(json_file_path):
    """
    将 JSON 文件（整体是一个列表）转换为 Hugging Face Dataset 格式。
    
    Args:
        json_file_path (str): JSON 文件的路径。
        
    Returns:
        dataset (datasets.Dataset): 转换后的数据集。
    """
    with open(json_file_path, 'r', encoding='utf-8') as f:
        try:
            # 直接读取整个 JSON 文件为一个列表
            data = json.load(f)
            
            # 确保 data 是一个包含字典的列表
            if isinstance(data, list) and all(isinstance(item, dict) for item in data):
                dataset = Dataset.from_list(data)
                return dataset
            else:
                raise ValueError("The JSON file does not contain a list of dictionaries.")
                
        except json.JSONDecodeError as e:
            print(f"Failed to decode JSON file: {json_file_path} - Error: {e}")
            raise

def upload_to_huggingface(dataset, dataset_name, token):
    """
    将数据集上传到 Hugging Face 数据集中心。
    
    Args:
        dataset (datasets.Dataset): 要上传的数据集。
        dataset_name (str): 数据集名称。
        token (str): Hugging Face 的 API token。
        
    Returns:
        None
    """
    # 设置 API Token
    HfFolder.save_token(token)
    api = HfApi()
    
    # 保存数据集到本地并上传
    dataset.push_to_hub(dataset_name, token=token)
    print(f"Dataset '{dataset_name}' uploaded successfully!")

if __name__ == "__main__":
    # 设置 JSON 文件路径、数据集名称和 Hugging Face API Token
    json_file_path = "/root/ARiSE/SWEbench/SWE-bench/swebench/versioning/results/bitflags-task-instances_versions.json"  # 替换为你的 JSON 文件路径
    dataset_name = "r1v3r/bitflags_version_dataset"  # 替换为你想要的数据集名称
    hf_token = os.environ.get("HUGGING_FACE_HUB_TOKEN", None)

    # 将 JSON 转换为数据集
    dataset = json_to_dataset(json_file_path)
    print("Dataset created successfully.")
    
    # 将数据集上传到 Hugging Face 数据集中心
    upload_to_huggingface(dataset, dataset_name, hf_token)
