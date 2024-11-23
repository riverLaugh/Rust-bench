from datasets import load_dataset

def filter_versions(dataset_name, dataset_split, version_key="version", id_key="instance_id", max_version=31.0, min_version=30.0):
    """
    下载 Hugging Face 数据集并筛选符合条件的对象，打印 instance_id 和去重的版本号。
    
    Args:
        dataset_name (str): 数据集名称(Hugging Face 数据集路径）。
        dataset_split (str): 数据集分割名（如 "train", "test"）。
        version_key (str): 数据集中表示版本号的字段名。
        id_key (str): 数据集中表示实例 ID 的字段名。
        max_version (float): 版本号的最大值（包含）。
    """
    # 下载数据集
    print(f"Downloading dataset '{dataset_name}', split '{dataset_split}'...")
    dataset = load_dataset(dataset_name, split=dataset_split)
    
    # 筛选出符合条件的对象
    print(f"Filtering objects where '{version_key}' <= {max_version}...")
    filtered_data = [item for item in dataset if version_key in item and (float(item[version_key]) <= max_version and float(item[version_key])>= min_version)]
    
    # 获取 instance_id 列表
    instance_ids = [item[id_key] for item in filtered_data if id_key in item]
    
    # 获取去重的版本号列表
    versions = {item[version_key] for item in filtered_data if version_key in item}
    
    print(f"instance count:{len(instance_ids)}")
    # 打印结果
    print("Instance IDs:")
    print(" ".join(map(str, instance_ids)))  # 空格连接 instance_id
    print("\nUnique Versions:")
    print(", ".join(sorted(map(str, versions))))  # 逗号连接去重的版本号

# 使用示例
if __name__ == "__main__":
    dataset_name = "r1v3r/arrow-rs"  # 替换为数据集名称
    dataset_split = "train"  # 替换为数据集分割
    version_key = "version"  # 替换为版本字段名
    id_key = "instance_id"   # 替换为实例 ID 字段名
    max_version = 53.2     # 最大版本号
    min_version = 51.0

    # 筛选并打印结果
    filter_versions(dataset_name, dataset_split, version_key, id_key, max_version,min_version)
