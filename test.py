from datasets import load_dataset

# 加载数据集（以 Hugging Face Hub 上的一个公开数据集为例）
dataset = load_dataset("Conard/fortune-telling")

# 将数据集保存为 JSON 文件
# dataset.to_json("dataset.json")
jsonsss = [example for example in dataset["train"]]
print(jsonsss[1])