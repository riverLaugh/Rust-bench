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




def main():
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


if __name__ == "__main__":
    
    main()


