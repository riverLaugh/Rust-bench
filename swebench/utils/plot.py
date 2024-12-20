import matplotlib.pyplot as plt
import numpy as np
from datasets import load_dataset
import tiktoken
from statistics import mean, median

# 加载 HuggingFace 数据集
dataset_name = "r1v3r/validated_12_18"  # 替换为您的数据集名称
dataset = load_dataset(dataset_name, split="train")

# 使用 tiktoken 对 problem_statement 分词
tokenizer = tiktoken.get_encoding("cl100k_base")  # 替换为您需要的编码器

# 提取 problem_statement 并统计 token 数
token_counts = []
for entry in dataset:
    problem_statement = entry["problem_statement"]
    tokens = tokenizer.encode(problem_statement)
    token_counts.append(len(tokens))

# 计算统计信息
min_tokens = min(token_counts)
max_tokens = max(token_counts)
mean_tokens = mean(token_counts)
median_tokens = median(token_counts)

# 打印统计信息
print(f"Token 数量最小值: {min_tokens}")
print(f"Token 数量最大值: {max_tokens}")
print(f"Token 数量平均值: {mean_tokens}")
print(f"Token 数量中位数: {median_tokens}")

# 绘制分布区间图
plt.figure(figsize=(10, 6))
counts, bins, patches = plt.hist(token_counts, bins=20, edgecolor='black', alpha=0.7)

# 在每个柱上显示具体的值
for count, bin_left, bin_right in zip(counts, bins[:-1], bins[1:]):
    plt.text(
        (bin_left + bin_right) / 2,  # 柱的中心位置
        count,                       # 柱的高度
        f"{int(count)}",             # 显示的文字
        ha="center", va="bottom"     # 水平居中，文字在柱的上方
    )

plt.title("Token 分布区间图")
plt.xlabel("Token 数量")
plt.ylabel("出现次数")
plt.grid(axis="y", alpha=0.75)
plt.show()