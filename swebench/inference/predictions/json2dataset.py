from datasets import Dataset, DatasetDict
from huggingface_hub import HfApi, HfFolder, Repository
import json
import os

def json_to_dataset(json_file_path):
    """
    将多行 JSON 文件转换为 Hugging Face Dataset 格式。
    
    Args:
        json_file_path (str): JSON 文件的路径。
        
    Returns:
        dataset (datasets.Dataset): 转换后的数据集。
    """
    data = []
    with open(json_file_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                # 每行解析一个 JSON 对象
                json_line = json.loads(line.strip())  # 去除行尾的空白符并解析 JSON
                data.append(json_line)
            except json.JSONDecodeError as e:
                print(f"Skipping invalid JSON line: {line.strip()} - Error: {e}")
    
    # 创建 Dataset 对象
    dataset = Dataset.from_list(data)
    return dataset

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
    json_file_path = "/home/riv3r/SWE-bench/swebench/versioning/results/output_validated.jsonl"  # 替换为你的 JSON 文件路径
    dataset_name = "r1v3r/bitflags_tests_dataset"  # 替换为你想要的数据集名称
    hf_token = os.environ.get("HUGGING_FACE_HUB_TOKEN", None)

    # 将 JSON 转换为数据集
    dataset = json_to_dataset(json_file_path)
    print("Dataset created successfully.")
    
    # 将数据集上传到 Hugging Face 数据集中心
    upload_to_huggingface(dataset, dataset_name, hf_token)
