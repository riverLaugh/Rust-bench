#!/bin/bash

# 设置脚本出错时立即退出
set -e

# 配置变量
PREDICTIONS_PATH="/root/ARiSE/SWEbench/swe-bench-example-preds.json" # 设置预测文件路径
DATASET_NAME="princeton-nlp/SWE-bench" # 数据集名称
RUN_ID="test0" # 测试运行 ID

echo "Starting End-to-End Pipeline..."

# 1. 数据收集阶段
echo "Step 1: Collecting data..."
cd make_repo

# 运行 make_repo.sh 脚本以创建仓库
if [ -f "./make_repo.sh" ]; then
    ./make_repo.sh
else
    echo "Error: make_repo.sh not found!"
    exit 1
fi

# 确保进入正确的分支（如 main 或 master）
BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$BRANCH" != "main" ] && [ "$BRANCH" != "master" ]; then
    echo "Warning: Not on main or master branch. You are on branch '$BRANCH'."
fi

# 进入 collect 文件夹并运行任务收集管道
cd collect
if [ -f "./run_tet_tasks_pipeline.sh" ]; then
    ./run_tet_tasks_pipeline.sh
else
    echo "Error: run_tet_tasks_pipeline.sh not found!"
    exit 1
fi
cd ../.. # 返回项目根目录

# 2. 版本控制阶段
echo "Step 2: Versioning..."
if [ -f "./run_get_version.sh" ]; then
    ./run_get_version.sh
else
    echo "Error: run_get_version.sh not found!"
    exit 1
fi

# 3. 推理阶段
echo "Step 3: Running Inference..."
cd inference/make_datasets

# 配置需要分割的数据集并运行分割脚本
if [ -f "./split_dataset.py" ]; then
    python3 split_dataset.py
else
    echo "Error: split_dataset.py not found!"
    exit 1
fi

# 生成数据集
if [ -f "./make_dataset.sh" ]; then
    ./make_dataset.sh
else
    echo "Error: make_dataset.sh not found!"
    exit 1
fi
cd .. # 返回到 inference 目录

# 运行 API 进行推理
if [ -f "./run_api.sh" ]; then
    ./run_api.sh
else
    echo "Error: run_api.sh not found!"
    exit 1
fi

# 4. 评估阶段
echo "Step 4: Evaluating Predictions..."
cd ..
# 检查 run_evaluation.py 的退出状态码
if [ $? -eq 0 ]; then
    echo "Evaluation completed successfully. Proceeding with further modifications..."

    # 使用 sed 命令更改目标文件内容
    sed -i 's/old_pattern/new_pattern/g' "$TARGET_FILE"

    # 再次运行某个命令
    echo "Re-running inference after modifications..."
    ./run_api.sh
else
    echo "Evaluation failed. Skipping further processing."
    exit 1
fi

echo "End-to-End Pipeline Completed Successfully!"
