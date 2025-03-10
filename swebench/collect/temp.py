import os
import shutil
from collections import defaultdict

def count_files_by_letter(directory):
    """
    统计指定目录下按字母开头且以 `.jsonl` 结尾的文件数量。
    :param directory: 文件夹路径
    :return: 字典，键为字母，值为文件数量
    """
    if not os.path.isdir(directory):
        raise ValueError(f"{directory} 不是有效的文件夹路径。")
    
    # 初始化字母统计字典
    letter_count = defaultdict(int)

    # 遍历文件夹下的所有文件
    for file_name in os.listdir(directory):
        # 检查是否是文件且以 `.jsonl` 结尾
        file_path = os.path.join(directory, file_name)
        if os.path.isfile(file_path) and file_name.endswith(".jsonl"):
            # 获取文件名第一个字母并转换为大写
            first_letter = file_name[0].upper()
            if 'A' <= first_letter <= 'Z':  # 判断是否是字母
                letter_count[first_letter] += 1
    
    return letter_count

def find_median_letter(letter_count):
    """
    找到文件数量的中位数所在的字母（按字典序）。
    :param letter_count: 字母统计字典
    :return: 中位数所在的字母
    """
    sorted_counts = sorted(letter_count.items())  # 按字母排序
    total_files = sum(letter_count.values())  # 总文件数
    median_index = (total_files - 1) // 2  # 中位数索引（0-based）

    # 遍历累积文件数，找到中位数所在的字母
    cumulative = 0
    for letter, count in sorted_counts:
        cumulative += count
        if cumulative > median_index:
            return letter

def move_files_by_letter(directory, target_directory, start_letter):
    """
    将以某个字母开头及之后字母的 `.jsonl` 文件移动到另一个文件夹。
    :param directory: 源文件夹路径
    :param target_directory: 目标文件夹路径
    :param start_letter: 起始字母
    """
    if not os.path.isdir(directory):
        raise ValueError(f"{directory} 不是有效的文件夹路径。")
    if not os.path.exists(target_directory):
        os.makedirs(target_directory)

    start_letter = start_letter.upper()
    if not ('A' <= start_letter <= 'Z'):
        raise ValueError("起始字母必须是 A 到 Z 之间的字母。")

    for file_name in os.listdir(directory):
        file_path = os.path.join(directory, file_name)
        if os.path.isfile(file_path) and file_name.endswith(".jsonl"):
            first_letter = file_name[0].upper()
            if first_letter >= start_letter:  # 判断是否需要移动
                shutil.move(file_path, os.path.join(target_directory, file_name))
                print(f"文件已移动: {file_name} -> {target_directory}")

if __name__ == "__main__":
    # 源文件夹路径
    source_directory = "/data/RustBench/SWE-bench/swebench/collect/tasks/auto"
    # 目标文件夹路径
    destination_directory = "/data/RustBench/SWE-bench/swebench/collect/tasks/auto2"

    # 获取统计结果
    try:
        result = count_files_by_letter(source_directory)

        # 输出统计结果
        print("文件数量统计（按字母开头，过滤 `.jsonl` 文件）：")
        for letter in sorted(result.keys()):
            print(f"{letter}: {result[letter]} 个文件")

        # 找到中位数所在的字母
        if result:
            median_letter = find_median_letter(result)
            print(f"\n文件数量的中位数在字母：{median_letter}")

            # 将中位数字母及之后的文件移动到目标文件夹
            move_files_by_letter(source_directory, destination_directory, median_letter)
            print(f"\n以字母 {median_letter} 开头及之后的 `.jsonl` 文件已移动到: {destination_directory}")
        else:
            print("\n目录中没有符合条件的 `.jsonl` 文件。")
    except ValueError as e:
        print(f"错误: {e}")
