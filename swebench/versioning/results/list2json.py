import json
from pathlib import Path

def file_to_jsonl(input_file_path: str, output_file_path: str):
    """
    将 JSON 文件中的数据逐行写入 JSONL 文件
    :param input_file_path: 输入的 JSON 文件路径
    :param output_file_path: 输出的 .jsonl 文件路径
    """
    # 读取文件内容，假设文件是一个标准的 JSON 数组
    with open(input_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)  # 解析为 Python 列表
    
    # 将数据逐行写入 .jsonl 文件
    with open(output_file_path, "w", encoding="utf-8") as f_out:
        for item in data:
            f_out.write(json.dumps(item) + "\n")  # 将每个元素写为一行 JSON 对象

# 示例
input_file = "/root/ARiSE/SWEbench/SWE-bench/swebench/versioning/results/bitflags-task-instances_versions.json"  # 输入的文件，假设是一个 JSON 数组
output_file = "/root/ARiSE/SWEbench/SWE-bench/swebench/versioning/results/output.jsonl"  # 输出的 .jsonl 文件

file_to_jsonl(input_file, output_file)
