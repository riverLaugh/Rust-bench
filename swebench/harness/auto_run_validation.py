import os
import subprocess
import logging

# 根路径
root_path = "/home/riv3r/SWE-bench/swebench"

# 配置路径
input_folder = os.path.join(root_path, "collect/tasks/auto")  # 存放 .jsonl 文件的文件夹
output_folder = os.path.join(root_path, "versioning/results")  # 存放结果文件的文件夹
version_folder = os.path.join(root_path, "versioning/auto/version")  # 存放版本信息的文件夹
env_commit_folder = os.path.join(root_path, "versioning/auto/env_commit")  # 存放环境设置 commit 的文件夹
versioning_log_folder = os.path.join(root_path, "versioning/auto/log")  # 存放日志文件的文件夹
dataset_folder = os.path.join(root_path, "versioning/auto/dataset")  # 存放数据集的文件夹
if not os.path.exists(output_folder):
    os.makedirs(output_folder)
if not os.path.exists(version_folder):
    os.makedirs(version_folder)
if not os.path.exists(env_commit_folder):
    os.makedirs(env_commit_folder)
if not os.path.exists(versioning_log_folder):
    os.makedirs(versioning_log_folder)
if not os.path.exists(dataset_folder):
    os.makedirs(dataset_folder)

num_workers = 16  # 并行线程数量

# 设置日志记录
log_file = os.path.join(versioning_log_folder, 'process.log')
log_file_detail = os.path.join(versioning_log_folder, 'process_detail.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, mode="w"),
        logging.StreamHandler()  # 可选：同时在终端显示
    ]
)

def run_command_with_logging(command, description):
    """
    运行命令并捕获日志
    """
    logging.info(f"Running: {description} -> {' '.join(command)}")
    with open(log_file_detail, 'w') as log:
        try:
            # 捕获子进程输出
            result = subprocess.run(
                command,
                stdout=log,
                stderr=log,
                text=True,
                check=True
            )
            return result
        except subprocess.CalledProcessError as e:
            logging.error(f"Error running {description}: {e}")
            return None


if __name__ == "__main__":
    # 遍历文件夹，找到所有 .jsonl 文件
    for root, dirs, files in os.walk(input_folder):
        for file in files:
            if file.endswith(".jsonl"):
                if "asterinas" in file:
                    continue
                logging.info(f"Processing: {file}")
                instances_path = os.path.join(root, file)
                base_name = os.path.splitext(file)[0]
                base_name = base_name.split(".")[0]
                version_path = version_folder + f"/{base_name}_versions.json"

                # Step 1: 运行 get_versions.py
                if not os.path.exists(version_path):
                    get_versions_command = [
                        "python", f"{root_path}/versioning/get_versions.py",
                        "--instances_path", instances_path,
                        "--retrieval_method", "github",
                        "--num_workers", str(num_workers),
                        "--output_dir", version_folder,
                        "--cleanup"
                    ]
                    run_command_with_logging(get_versions_command, f"get_versions {file}")

                # Step 2: 运行 environment_setup_commit.py
                if not os.path.exists(f"{root_path}/versioning/auto/dataset/{base_name}_versions.json"):
                    environment_setup_command = [
                        "python", f"{root_path}/versioning/environment_setup_commit.py",
                        "--dataset_name", version_path,
                        "--output_dir", dataset_folder
                    ]
                    result = run_command_with_logging(environment_setup_command, f"environment_setup_commit {file}")
                    if result is None:
                        os.remove(version_path)
                        continue

                # Step 3: 运行 run_validation.py
                run_validation_command = [
                    "python", "run_validation.py",
                    "--dataset_name", f"{root_path}/versioning/auto/dataset/{base_name}_versions.json",
                    "--run_id", f"{base_name}_versions",
                    "--max_workers", str(num_workers),
                    "--cache_level", "base",
                    "--auto", "True"
                ]
                run_command_with_logging(run_validation_command, f"run_validation {file}")
    logging.info("All tasks completed.")
