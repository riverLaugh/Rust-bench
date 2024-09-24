import argparse
from datasets import load_dataset

def main(args):
    # Step 1: 加载 jsonl 文件
    dataset = load_dataset("json", data_files={"data": args.data_file})

    # Step 2: 划分 train 和 test 集合
    train_test_split = dataset['data'].train_test_split(test_size=args.test_size)

    # Step 3: 保存数据集
    save_path = args.save_path if args.save_path.endswith('/') else args.save_path + '/'
    dataset_name = args.dataset_name if args.dataset_name else 'dataset'
    train_test_split.save_to_disk(save_path + dataset_name)

    print(f"数据集已成功保存到 {save_path}{dataset_name}!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="将 jsonl 文件转换为 Hugging Face 数据集，并进行训练集和测试集划分。")
    
    # 添加命令行参数
    parser.add_argument(
        "--data_file", 
        type=str, 
        required=True, 
        help="输入的 jsonl 文件路径"
    )
    
    parser.add_argument(
        "--dataset_name", 
        type=str, 
        required=False, 
        default="splitted_dataset",
        help="数据集的名称（用于保存）"
    )
    
    parser.add_argument(
        "--save_path", 
        type=str, 
        required=True, 
        help="保存数据集的目录路径"
    )
    
    parser.add_argument(
        "--test_size", 
        type=float, 
        default=0.2, 
        help="测试集所占比例（默认为 0.2）"
    )

    args = parser.parse_args()
    main(args)
