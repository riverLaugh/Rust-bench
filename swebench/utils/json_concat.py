import os
import json
from dataset_utils import List2dataset,upload_to_huggingface
from datasets import Dataset

def merge_json_files(folder_path):
    """
    合并指定文件夹下匹配 'arrow-rs_validated-*.json' 格式的文件为一个JSON文件。

    :param folder_path: 文件夹路径
    :param output_file: 输出文件路径
    """
    merged_data = []

    # 遍历文件夹，找到匹配的文件
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.startswith("arrow-rs_validated-") and file.endswith(".json"):
                file_path = os.path.join(root, file)
                try:
                    # 读取JSON文件内容
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # 将内容添加到列表中
                        if isinstance(data, list):
                            merged_data.extend(data)
                        else:
                            merged_data.append(data)
                except Exception as e:
                    print(f"Error reading file {file_path}: {e}")

    # 将合并的数据写入输出文件
    dataset= Dataset.from_list(merged_data)
    upload_to_huggingface(dataset=dataset,dataset_name="r1v3r/arrow_validated")

if __name__ == "__main__":
    # 指定文件夹路径和输出文件路径
    folder_path = "/home/riv3r/SWE-bench/swebench/harness/results"
    
    merge_json_files(folder_path)
