import os
from datasets import load_dataset, Dataset, concatenate_datasets
from huggingface_hub import login, HfApi, create_repo, Repository
import json

# ================== 配置部分 ==================

# 从环境变量中获取 Hugging Face Hub 令牌
hf_token = os.getenv("HUGGING_FACE_HUB_TOKEN")
if not hf_token:
    raise ValueError("请设置环境变量 'HUGGING_FACE_HUB_TOKEN'。")

# 需要合并的两个数据集的名称或路径
# 例如，公共数据集可以使用格式 'username/dataset_name'
dataset1_name = "r1v3r/auto_validated2"  # 请替换为第一个数据集的实际名称
dataset2_name = "r1v3r/auto_validated"  # 请替换为第二个数据集的实际名称
dataset3_name = "r1v3r/RustGPT_Bench_100"  # 第三个数据集的名称或路径

# 上传合并后数据集的目标仓库名称
# 该仓库将被创建在您的账户下
merged_dataset_name = "r1v3r/auto_0207"  # 请替换为目标数据集名称

# 定义用于去重的列（根据数据集结构调整）
dedup_columns = ["instance_id"]  # 例如，使用 'id' 列进行去重

# 可选：自定义数据集描述
dataset_description = """
这是合并自 dataset1 和 dataset2 的数据集。去除了重复的条目。
"""

# ================== 登录 Hugging Face Hub ==================

def login_to_hf(token):
    """
    使用提供的令牌登录 Hugging Face Hub。
    """
    try:
        login(token=token)
        print("成功登录 Hugging Face Hub。")
    except Exception as e:
        print(f"登录失败: {e}")
        raise

# ================== 拉取数据集 ==================

def fetch_datasets(dataset1, dataset2, dataset3):
    """
    从 Hugging Face Hub 拉取三个数据集。

    Args:
        dataset1 (str): 第一个数据集的名称或路径。
        dataset2 (str): 第二个数据集的名称或路径。
        dataset3 (str): 第三个数据集的名称或路径。

    Returns:
        tuple: 包含三个 Dataset 对象。
    """
    try:
        ds1 = load_dataset(dataset1, split="train")
        print(f"成功加载数据集：{dataset1}，包含 {len(ds1)} 条数据。")
    except Exception as e:
        print(f"无法加载数据集 {dataset1}: {e}")
        raise

    try:
        ds2 = load_dataset(dataset2, split="train")
        print(f"成功加载数据集：{dataset2}，包含 {len(ds2)} 条数据。")
    except Exception as e:
        print(f"无法加载数据集 {dataset2}: {e}")
        raise
    
    try:
        ds3 = load_dataset(dataset3, split="train")
        print(f"成功加载数据集：{dataset3}，包含 {len(ds3)} 条数据。")
    except Exception as e:
        print(f"无法加载数据集 {dataset3}: {e}")
        raise

    return ds1, ds2, ds3

# ================== 去重合并 ==================

def merge_and_deduplicate(ds1, ds2, ds3, dedup_cols):
    """
    合并三个数据集并去重。

    Args:
        ds1 (Dataset): 第一个数据集。
        ds2 (Dataset): 第二个数据集。
        ds3 (Dataset): 第三个数据集。
        dedup_cols (list): 用于去重的列名列表。

    Returns:
        Dataset: 合并并去重后的数据集。
    """
    # 合并数据集
    merged_ds = concatenate_datasets([ds1, ds2, ds3])
    print(f"合并后数据集包含 {len(merged_ds)} 条数据。")

    # 去重
    merged_df = merged_ds.to_pandas()
    deduped_df = merged_df.drop_duplicates(subset=dedup_cols)
    print(f"去重后数据集包含 {len(deduped_df)} 条数据。")

    # 转换回 Dataset 对象
    deduped_ds = Dataset.from_pandas(deduped_df)
    return deduped_ds

# ================== 上传数据集 ==================

def upload_dataset(deduped_ds, repo_name, description):
    """
    将合并后的数据集上传到 Hugging Face Hub。

    Args:
        deduped_ds (Dataset): 去重后的数据集。
        repo_name (str): 目标仓库的名称。
        description (str): 数据集描述。

    Returns:
        None
    """
    api = HfApi()

    # 检查仓库是否已存在
    try:
        api.repo_info(repo_name)
        print(f"仓库 {repo_name} 已存在。")
    except Exception:
        # 如果仓库不存在，则创建
        try:
            api.create_repo(repo_name, exist_ok=True, private=False)
            print(f"成功创建仓库 {repo_name}。")
        except Exception as e:
            print(f"无法创建仓库 {repo_name}: {e}")
            raise

    # 保存合并后的数据集为本地文件（例如，CSV 或 JSON）
    output_file = "merged_dataset.json"
    deduped_ds.to_json(output_file)
    print(f"已将合并后的数据集保存为 {output_file}。")

    # 使用 `push_to_hub` 方法将数据集上传
    try:
        deduped_ds.push_to_hub(repo_name, private=False)
        print(f"成功上传数据集到 Hugging Face Hub：{repo_name}")
    except Exception as e:
        print(f"上传失败: {e}")
        raise

# ================== 主函数 ==================
def main():
    # 登录
    login_to_hf(hf_token)

    # 拉取数据集
    ds1, ds2, ds3 = fetch_datasets(dataset1_name, dataset2_name, dataset3_name)

    # 合并与去重
    merged_ds = merge_and_deduplicate(ds1, ds2, ds3, dedup_columns)

    # 上传合并后的数据集
    upload_dataset(merged_ds, merged_dataset_name, dataset_description)


if __name__ == "__main__":
    main()
