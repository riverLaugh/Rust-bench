import os,json
from typing import Dict
from datetime import datetime
import datetime
from typing import Dict, List, Tuple

def get_file_names(directory):
    """
    获取指定目录下所有文件的文件名，并返回一个列表。
    :param directory: 目标目录路径
    :return: 文件名列表
    """
    if not os.path.isdir(directory):
        raise ValueError(f"{directory} 不是有效的目录路径。")
    
    file_names = []
    
    # 遍历目录中的所有文件和子目录
    for root, dirs, files in os.walk(directory):
        for file in files:
            # 将文件名添加到列表中
            file_names.append(file)
    
    return file_names

def extract_repositories_names(file_names):
    """
    将一个目录下所有的文件名 rpos-mode-tasks.json ...中的repos名提取出来

    :return repos名列表
    """
    repositories = []

    for n in file_names:
        repository_name = n.split("-")[0]
        repositories.append(repository_name)

    return repositories


def count_instances(json_path):
    """
    统计 JSON 文件中的实例数量
    
    Args:
        json_path (str): JSON 文件的路径
    
    Returns:
        int: 实例数量
    """
    count = 0
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            # 按行读取文件
            for line in f:
                line = line.strip()
                if line:  # 跳过空行
                    try:
                        # 尝试解析每一行的 JSON 对象
                        json.loads(line)
                        count += 1
                    except json.JSONDecodeError:
                        continue
        
        return count
    
    except FileNotFoundError:
        print(f"错误: 找不到文件 '{json_path}'")
        return 0
    except Exception as e:
        print(f"错误: 读取文件时发生异常: {str(e)}")
        return 0
    
def count_all_jsonl_files(directory: str) -> Dict[str, int]:
    """
    统计指定目录下所有 .jsonl 文件的实例数量
    
    Args:
        directory (str): 要搜索的目录路径
    
    Returns:
        Dict[str, int]: 按实例数量降序排序的字典 {文件名: 实例数量}
    """
    result_dict = {}
    
    # 遍历目录
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.jsonl'):
                full_path = os.path.join(root, file)
                count = count_instances(full_path)
                result_dict[file] = count
    
    # 按值降序排序
    sorted_dict = dict(sorted(result_dict.items(), 
                            key=lambda item: item[1], 
                            reverse=True))
    
    return sorted_dict

def save_statistics_to_file(directory: str, output_dir: str = "statistics") -> str:
    """
    统计目录下所有 .jsonl 文件的实例数量并保存结果
    
    Args:
        directory (str): 要搜索的目录路径
        output_dir (str): 输出目录路径，默认为 'statistics'
    
    Returns:
        str: 保存的文件路径
    """
    # 获取统计结果
    results = count_all_jsonl_files(directory)
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 生成带时间戳的文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"jsonl_statistics_{timestamp}.json")
    
    # 准备要保存的数据
    output_data = {
        "统计时间": datetime.now().isoformat(),
        "扫描目录": os.path.abspath(directory),
        "文件统计": results
    }
    
    # 保存到文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
    
    return output_file

import json
import os
import datetime
from typing import Dict, List, Tuple

def classify_instances_by_time(json_files_dir: str, cutoff_time: str) -> Dict[str, Dict[str, List]]:
    """
    根据指定时间对JSON文件中的实例进行分类
    
    Args:
        json_files_dir (str): 包含JSON文件的目录
        cutoff_time (str): 分界时间，格式为"YYYY-MM-DDTHH:MM:SSZ"
    
    Returns:
        Dict[str, Dict[str, List]]: 分类结果，格式为:
        {
            "json文件名": {
                "earlier": [实例列表],
                "later": [实例列表]
            }
        }
    """
    # 将输入的时间字符串转换为datetime对象
    cutoff_datetime = datetime.datetime.strptime(cutoff_time, "%Y-%m-%dT%H:%M:%SZ")
    
    # 结果字典
    result = {}
    
    # 遍历目录中的所有文件
    for file_name in os.listdir(json_files_dir):
        if file_name.endswith('.jsonl'):
            file_path = os.path.join(json_files_dir, file_name)
            
            # 初始化该文件的分类结果
            result[file_name] = {
                "earlier": [],  # 早于截止时间的实例
                "later": []     # 晚于截止时间的实例
            }
            
            try:
                # 读取JSON文件
                instances = []
                with open(file_path, 'r', encoding='utf-8') as f:
                    # 尝试作为整个JSON对象读取
                    try:
                        content = json.load(f)
                        # 如果是列表形式
                        if isinstance(content, list):
                            instances = content
                        # 如果每一行是单独的JSON对象
                        else:
                            instances = [content]
                    except json.JSONDecodeError:
                        # 如果不是有效的整个JSON，尝试按行读取
                        f.seek(0)  # 重置文件指针到开头
                        for line in f:
                            line = line.strip()
                            if line:
                                try:
                                    instance = json.loads(line)
                                    instances.append(instance)
                                except json.JSONDecodeError:
                                    continue
                
                # 对实例进行分类
                for instance in instances:
                    if "created_at" in instance:
                        try:
                            instance_time = datetime.datetime.strptime(
                                instance["created_at"], 
                                "%Y-%m-%dT%H:%M:%SZ"
                            )
                            
                            # 判断实例时间与截止时间的关系
                            if instance_time < cutoff_datetime:
                                result[file_name]["earlier"].append(instance)
                            else:
                                result[file_name]["later"].append(instance)
                        except ValueError:
                            # 如果日期格式不匹配，跳过该实例
                            print(f"警告: 文件 {file_name} 中的实例包含无效的时间格式: {instance.get('created_at', 'unknown')}")
                            continue
                    else:
                        # 如果实例中没有created_at字段，则跳过
                        print(f"警告: 文件 {file_name} 中的实例缺少 'created_at' 字段")
                        continue
                        
                # 打印分类结果
                print(f"文件 {file_name} 分类完成:")
                print(f"  早于 {cutoff_time} 的实例数: {len(result[file_name]['earlier'])}")
                print(f"  晚于 {cutoff_time} 的实例数: {len(result[file_name]['later'])}")
                    
            except Exception as e:
                print(f"处理文件 {file_name} 时出错: {str(e)}")
                continue
    
    return result

def classify_instances_by_time2(json_files_dir: str, cutoff_time: str) -> Dict[str, Dict[str, Dict[str, int]]]:
    """
    根据指定时间对JSONL文件中的实例进行分类，并按仓库名统计数量
    
    Args:
        json_files_dir (str): 包含JSONL文件的目录
        cutoff_time (str): 分界时间，格式为"YYYY-MM-DDTHH:MM:SSZ"
    
    Returns:
        Dict[str, Dict[str, Dict[str, int]]]: 分类结果，格式为:
        {
            "earlier": {"repo1": count1, "repo2": count2, ...},
            "later": {"repo1": count1, "repo2": count2, ...}
        }
    """
    # 将输入的时间字符串转换为datetime对象
    cutoff_datetime = datetime.datetime.strptime(cutoff_time, "%Y-%m-%dT%H:%M:%SZ")
    
    # 结果字典
    result = {
        "earlier": {},  # 早于截止时间的实例统计 {repo: count}
        "later": {}     # 晚于截止时间的实例统计 {repo: count}
    }
    
    # 文件计数器
    file_count = 0
    processed_count = 0
    
    # 遍历目录中的所有文件
    for file_name in os.listdir(json_files_dir):
        if file_name.endswith('.jsonl'):
            file_count += 1
            file_path = os.path.join(json_files_dir, file_name)
            
            # 当前文件的统计计数
            earlier_count = 0
            later_count = 0
            
            try:
                # 按行读取JSONL文件
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if not line:
                            continue
                            
                        try:
                            instance = json.loads(line)
                            
                            # 提取仓库名称
                            repo = instance.get("repo", "unknown")
                            
                            # 检查创建时间
                            if "created_at" in instance:
                                try:
                                    instance_time = datetime.datetime.strptime(
                                        instance["created_at"], 
                                        "%Y-%m-%dT%H:%M:%SZ"
                                    )
                                    
                                    # 判断实例时间与截止时间的关系
                                    if instance_time < cutoff_datetime:
                                        # 早于截止时间
                                        earlier_count += 1
                                        # 更新仓库统计
                                        if repo in result["earlier"]:
                                            result["earlier"][repo] += 1
                                        else:
                                            result["earlier"][repo] = 1
                                    else:
                                        # 晚于截止时间
                                        later_count += 1
                                        # 更新仓库统计
                                        if repo in result["later"]:
                                            result["later"][repo] += 1
                                        else:
                                            result["later"][repo] = 1
                                except ValueError:
                                    print(f"警告: 文件 {file_name} 第 {line_num} 行包含无效的时间格式")
                                    continue
                            else:
                                print(f"警告: 文件 {file_name} 第 {line_num} 行缺少 'created_at' 字段")
                                continue
                                
                        except json.JSONDecodeError as e:
                            print(f"警告: 文件 {file_name} 第 {line_num} 行不是有效的JSON: {str(e)}")
                            continue
                
                processed_count += 1
                print(f"文件 {file_name} 分类完成:")
                print(f"  早于 {cutoff_time} 的实例数: {earlier_count}")
                print(f"  晚于 {cutoff_time} 的实例数: {later_count}")
                    
            except Exception as e:
                print(f"处理文件 {file_name} 时出错: {str(e)}")
                continue
    
    print(f"\n总计: 发现 {file_count} 个JSONL文件，成功处理了 {processed_count} 个文件")
    return result

def save_classification_results2(classification: Dict[str, Dict[str, int]], output_dir: str, cutoff_time: str) -> Tuple[str, str]:
    """
    将分类结果保存为两个JSON文件：一个包含早期统计，一个包含晚期统计
    
    Args:
        classification (Dict): classify_instances_by_time的返回结果
        output_dir (str): 输出目录
        cutoff_time (str): 用于生成文件名的时间
    
    Returns:
        Tuple[str, str]: (早期统计文件路径, 晚期统计文件路径)
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # 定义输出文件名
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    cutoff_simple = cutoff_time.replace(":", "_").replace("-", "_").replace("T", "_").replace("Z", "")
    
    earlier_file = os.path.join(output_dir, f"repos_before_{cutoff_simple}_{timestamp}.json")
    later_file = os.path.join(output_dir, f"repos_after_{cutoff_simple}_{timestamp}.json")
    
    # 获取早期和晚期的仓库统计
    earlier_stats = classification["earlier"]
    later_stats = classification["later"]
    
    # 按值降序排序
    earlier_stats_sorted = dict(sorted(earlier_stats.items(), key=lambda item: item[1], reverse=True))
    later_stats_sorted = dict(sorted(later_stats.items(), key=lambda item: item[1], reverse=True))
    
    # 计算总计数
    earlier_total = sum(earlier_stats.values())
    later_total = sum(later_stats.values())
    
    # 准备输出数据
    earlier_output = {
        "cutoff_time": cutoff_time,
        "total_count": earlier_total,
        "repo_counts": earlier_stats_sorted
    }
    
    later_output = {
        "cutoff_time": cutoff_time,
        "total_count": later_total,
        "repo_counts": later_stats_sorted
    }
    
    # 保存早期统计
    with open(earlier_file, 'w', encoding='utf-8') as f:
        json.dump(earlier_output, f, ensure_ascii=False, indent=2)
    
    # 保存晚期统计
    with open(later_file, 'w', encoding='utf-8') as f:
        json.dump(later_output, f, ensure_ascii=False, indent=2)
    
    print(f"早于 {cutoff_time} 的仓库统计 (共 {earlier_total} 个实例) 已保存到: {earlier_file}")
    print(f"晚于 {cutoff_time} 的仓库统计 (共 {later_total} 个实例) 已保存到: {later_file}")
    
    return earlier_file, later_file

def save_classification_results(classification: Dict[str, Dict[str, List]], output_dir: str, cutoff_time: str) -> Tuple[str, str]:
    """
    将分类结果保存为两个JSON文件：一个包含早期实例，一个包含晚期实例
    
    Args:
        classification (Dict): classify_instances_by_time的返回结果
        output_dir (str): 输出目录
        cutoff_time (str): 用于生成文件名的时间
    
    Returns:
        Tuple[str, str]: (早期实例文件路径, 晚期实例文件路径)
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # 定义输出文件名
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    cutoff_simple = cutoff_time.replace(":", "_").replace("-", "_").replace("T", "_").replace("Z", "")
    
    earlier_file = os.path.join(output_dir, f"instances_before_{cutoff_simple}_{timestamp}.json")
    later_file = os.path.join(output_dir, f"instances_after_{cutoff_simple}_{timestamp}.json")
    
    # 合并所有文件中的早期实例和晚期实例
    all_earlier = []
    all_later = []
    
    for file_name, categories in classification.items():
        all_earlier.extend(categories["earlier"])
        all_later.extend(categories["later"])
    
    # 保存早期实例
    with open(earlier_file, 'w', encoding='utf-8') as f:
        json.dump({
            "cutoff_time": cutoff_time,
            "instance_count": len(all_earlier),
            "instances": all_earlier
        }, f, ensure_ascii=False, indent=2)
    
    # 保存晚期实例
    with open(later_file, 'w', encoding='utf-8') as f:
        json.dump({
            "cutoff_time": cutoff_time,
            "instance_count": len(all_later),
            "instances": all_later
        }, f, ensure_ascii=False, indent=2)
    
    print(f"早于 {cutoff_time} 的 {len(all_earlier)} 个实例已保存到: {earlier_file}")
    print(f"晚于 {cutoff_time} 的 {len(all_later)} 个实例已保存到: {later_file}")
    
    return earlier_file, later_file

def merge_classification_results(results_list):
    """
    合并多个分类结果字典
    
    Args:
        results_list (list): 包含多个分类结果字典的列表
    
    Returns:
        Dict: 合并后的分类结果字典
    """
    merged_result = {
        "earlier": {},
        "later": {}
    }
    
    # 遍历所有分类结果
    for result in results_list:
        # 合并早期统计
        for repo, count in result["earlier"].items():
            if repo in merged_result["earlier"]:
                merged_result["earlier"][repo] += count
            else:
                merged_result["earlier"][repo] = count
        
        # 合并晚期统计
        for repo, count in result["later"].items():
            if repo in merged_result["later"]:
                merged_result["later"][repo] += count
            else:
                merged_result["later"][repo] = count
    
    # 对结果进行降序排序（实际排序会在保存时进行，这里只是返回合并的结果）
    return merged_result

def split_all_tasks_by_time(cutoff_time,output_dir):
        # 指定要读取的目录路径
    directory_path_auto1 = "/data/RustBench/SWE-bench/swebench/collect/tasks/auto"
    directory_path_auto2 = "/data/RustBench/SWE-bench/swebench/collect/tasks/auto2"
    directory_path_auto3 = "/data/RustBench/SWE-bench/swebench/collect/tasks/auto3"

    # 分类实例
    classification_result1 = classify_instances_by_time2(directory_path_auto1, cutoff_time)
    classification_result2 = classify_instances_by_time2(directory_path_auto2, cutoff_time)
    classification_result3 = classify_instances_by_time2(directory_path_auto3, cutoff_time)

    merged_result = merge_classification_results([
    classification_result1, 
    classification_result2,
    classification_result3
    ])

    # 保存结果
    earlier_file, later_file = save_classification_results2(merged_result, output_dir, cutoff_time)
    


# 使用示例
if __name__ == "__main__":
    
    cutoff_time = "2024-04-01T00:00:00Z"
    output_dir = "/data/RustBench/SWE-bench/swebench/collect/statistics"

    directory_path_auto1 = "/data/RustBench/SWE-bench/swebench/collect/tasks/auto"
    directory_path_auto2 = "/data/RustBench/SWE-bench/swebench/collect/tasks/auto2"
    directory_path_auto3 = "/data/RustBench/SWE-bench/swebench/collect/tasks/auto3"
    # file_path="/data/RustBench/SWE-bench/swebench/collect/rust_repos_diff_227.json"

    split_all_tasks_by_time(cutoff_time,output_dir)


    # # 分类实例
    # classified = classify_instances_by_time(directory_path_auto1, cutoff_time)
    # # 保存结果
    # earlier_file, later_file = save_classification_results(classified, output_dir, cutoff_time)
    
    # with open(file_path,'r') as f:
    #     content = json.load(f)
    #     for i in range(len(content)):
    #         content[i] = content[i].split("/")[1]

    # # print(content)
    # print(len(content))


    # auto1 = count_all_jsonl_files(directory_path_auto1)
    # output_path1 = save_statistics_to_file(directory_path_auto1)
    # print(f"统计结果1已保存到: {output_path1}")
    # output_path2 = save_statistics_to_file(directory_path_auto2)
    # print(f"统计结果2已保存到: {output_path2}")
    # output_path3 = save_statistics_to_file(directory_path_auto3)
    # print(f"统计结果3已保存到: {output_path3}")
    
    

    # try:
    #     # 获取所有文件的repository
    #     file_names_auto1 = get_file_names(directory_path_auto1)
    #     repositories_auto1 = extract_repositories_names(file_names_auto1)

    #     file_names_auto2 = get_file_names(directory_path_auto2)
    #     repositories_auto2 = extract_repositories_names(file_names_auto2)

    #     file_names_auto3 = get_file_names(directory_path_auto3)
    #     repositories_auto3 = extract_repositories_names(file_names_auto3)

    #     repositories_auto1 = list(set(repositories_auto1))

    #     # auto2 ...
    #     repositories_auto2 = list(set(repositories_auto2))
    #     # print(repositories_auto2)
    #     # print(len(repositories_auto2))

    #     # auto3 目录下所有文件的repository name
    #     repositories_auto3 = list(set(repositories_auto3))
    #     # print(repositories_auto3)
    #     # print(len(repositories_auto3))
    
    #     # content_set = set(content)
    #     repos_auto1 = set(repositories_auto1)
    #     repos_auto2 = set(repositories_auto2)
    #     repos_auto3 = set(repositories_auto3)

    #     # print(len(repos_auto3))

    #     # diff = content_set - repos_auto2 - repos_auto1
    #     # diff = list(diff)
    #     # print(diff,len(diff))
    #     # print(len(content))

    # except ValueError as e:
    #     print(f"错误: {e}")
