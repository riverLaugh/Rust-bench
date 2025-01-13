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

num_workers = 16  # 并行线程数量

# 设置日志记录
log_file = os.path.join(versioning_log_folder, 'process.log')
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler(log_file,mode="w"), logging.StreamHandler()])

# 遍历文件夹，找到所有 .jsonl 文件
for root, dirs, files in os.walk(input_folder):
    for file in files:
        if file.endswith(".jsonl"):
            # 构造文件路径
            if "asterinas" in file:
                continue
            logging.info(f"Processing: {file}")
            instances_path = os.path.join(root, file)
            base_name = os.path.splitext(file)[0]  # 去掉扩展名
            
            # Step 1: 运行 get_versions.py
            get_versions_command = [
                "python", "/home/riv3r/SWE-bench/swebench/versioning/get_versions.py",
                "--instances_path", instances_path,
                "--retrieval_method", "github",
                "--num_workers", str(num_workers),
                "--output_dir", version_folder,
                "--cleanup"
            ]
            logging.info(f"Running: get_versions {file}")
            try:
                subprocess.run(get_versions_command, check=True)
            except subprocess.CalledProcessError as e:
                logging.error(f"Error running get_versions.py for {file}: {e}")
                continue
            #split 是为了解决仓库名字中有.rs的问题
            version_path = version_folder + f"/{base_name.split('.')[0]}_versions.json"
            # Step 2: 运行 environment_setup_commit.py
            environment_setup_command = [
                "python", "/home/riv3r/SWE-bench/swebench/versioning/environment_setup_commit.py",
                "--dataset_name", version_path,
                "--output_dir", dataset_folder
            ]
            logging.info(f"Running: {' '.join(environment_setup_command)}")
            try:
                subprocess.run(environment_setup_command, check=True)
            except subprocess.CalledProcessError as e:
                os.remove(version_path)
                logging.error(f"Error running environment_setup_commit.py for {file}: {e}")
                continue

            # Step 3: 运行 run_validation.py（如果需要）
            run_validation_command = [
                "python", "run_validation.py",
                "--dataset_name", f"/home/riv3r/SWE-bench/swebench/versioning/auto/dataset/{base_name}_versions.json",
                "--run_id", f"{base_name}_versions",
                "--max_workers", str(num_workers),
                "--cache_level", "base",
                "--auto", "True"
            ]
            logging.info(f"Running: {' '.join(run_validation_command)}")
            try:
                subprocess.run(run_validation_command, check=True)
            except subprocess.CalledProcessError as e:
                logging.error(f"Error running run_validation.py for {file}: {e}")
                continue

logging.info("All tasks completed.")
