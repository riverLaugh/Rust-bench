import json
import os
import time
from datasets import Dataset
from huggingface_hub import HfApi, HfFolder
import schedule
from datetime import datetime
import re

# Hugging Face 配置
HF_USERNAME = "r1v3r"
HF_TOKEN = os.getenv("HUGGING_FACE_HUB_TOKEN", None)
REPO_NAME = "auto_validated"  # 数据集名称

# JSON 文件路径
JSON_FILE_PATH = "/home/riv3r/SWE-bench/swebench/harness/results/auto/defaultconfig_validated.json"
LAST_UPLOAD_COUNT_FILE = "/tmp/last_upload_count.txt"  # 临时文件，用于存储上次上传的实例数量


def post_process_data(func):
    def wrapper(*args, **kwargs):

        retval = func(*args, **kwargs)

        time_re = re.compile(r"(\d{4})-(\d{2})-(\d{2})(?:T| )(\d{2}):(\d{2}):(\d{2})Z?")

        for data in retval:

            # 1. 将时间字符串转为毫秒级整数时间戳
            if isinstance(data["created_at"], str):
                time_match = re.match(time_re, data["created_at"])
                if time_match:
                    data["created_at"] = int(
                        datetime.strptime(
                            f"{time_match.group(1)}-{time_match.group(2)}-{time_match.group(3)}T{time_match.group(4)}:{time_match.group(5)}:{time_match.group(6)}",
                            "%Y-%m-%dT%H:%M:%S",
                        ).timestamp() * 1000
                    )

        return retval

    return wrapper


@post_process_data
def load_json(file_path):
    with open(file_path, "r") as f:
        data = json.load(f)
    return data


def convert_to_hf_dataset(data):
    return Dataset.from_list(data)


def upload_to_hf(dataset, repo_name, token):
    # 推送数据集到 Hugging Face Hub
    dataset.push_to_hub(repo_name, token=token)


def get_last_upload_count():
    """读取上次上传时记录的实例数量"""
    if os.path.exists(LAST_UPLOAD_COUNT_FILE):
        with open(LAST_UPLOAD_COUNT_FILE, "r") as f:
            return int(f.read().strip())
    return 0


def save_current_upload_count(count):
    """保存当前实例数量到文件"""
    with open(LAST_UPLOAD_COUNT_FILE, "w") as f:
        f.write(str(count))


def main():
    # 1. 加载 JSON 数据
    if not os.path.exists(JSON_FILE_PATH):
        print(f"JSON file not found: {JSON_FILE_PATH}")
        return

    data = load_json(JSON_FILE_PATH)
    current_count = len(data)
    print(f"Loaded {current_count} records from JSON.")

    # 2. 获取上次上传的实例数量
    last_count = get_last_upload_count()
    print(f"Last upload count: {last_count}")

    # 3. 检查实例数量是否增加
    if current_count > last_count:
        print("New instances detected. Preparing to upload...")
        # 转换为 Hugging Face 数据集
        hf_dataset = convert_to_hf_dataset(data)
        print("Converted data to Hugging Face Dataset.")

        # 上传到 Hugging Face
        upload_to_hf(hf_dataset, REPO_NAME, HF_TOKEN)
        print(f"Dataset uploaded to Hugging Face: {HF_USERNAME}/{REPO_NAME}")

        # 更新上次上传的实例数量
        save_current_upload_count(current_count)
    else:
        print("No new instances detected. Skipping upload.")


if __name__ == "__main__":
    main()
    # 每隔 12 小时运行一次
    schedule.every(1).hours.do(main)

    while True:
        schedule.run_pending()
        time.sleep(600)
