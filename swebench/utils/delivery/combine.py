import json

def merge_json_files(entry_file, response_file, output_file):
    """
    读取两个 JSON 文件，根据 instance_id 合并，并保存为 JSONL 文件。

    :param entry_file: 包含代码片段等信息的 JSON 文件路径。
    :param response_file: 包含问题类型等信息的 JSON 文件路径。
    :param output_file: 输出 JSONL 文件路径。
    """
    # 读取 entry 文件内容
    with open(entry_file, 'r', encoding='utf-8') as f:
        entry_data = json.load(f)
    
    # 读取 response 文件内容
    with open(response_file, 'r', encoding='utf-8') as f:
        response_data = json.load(f)
    
    # 构建合并后的数据
    with open(output_file, 'w', encoding='utf-8') as f:
        for entry in entry_data:
            # 查找匹配的 response 数据
            matching_response = next((r for r in response_data if r["instance_id"] == entry["instance_id"]), None)
            if matching_response:
                merged_json = {
                    "code_snippet": entry["code_snippet"],
                    "target_function": entry["target_function"],
                    "review_type": entry["review_type"],
                    "issue_detail": {
                        "problem_type": matching_response["problem_type"],
                        "location": entry["issue_detail"]["location"],
                        "level": matching_response["severity_level"],
                        "description": matching_response["description"],
                        "level_reason": matching_response["reason"]
                    },
                    "repo": entry["repo"],
                    "branch": entry["branch"],
                    "file_path": entry["file_path"],
                    "language": entry["language"]
                }
                # 将每条记录写入 JSONL 文件
                f.write(json.dumps(merged_json, ensure_ascii=False) + '\n')
    print(f"Merged JSONL saved to {output_file}")

# 示例用法
entry_file_path = '/home/riv3r/SWE-bench/swebench/utils/delivery/entries.json'  # 第一个 JSON 文件路径
response_file_path = '/home/riv3r/SWE-bench/swebench/utils/delivery/classification_results_cn.json'  # 第二个 JSON 文件路径
output_file_path = '/home/riv3r/SWE-bench/swebench/utils/delivery/siada_edu_case.jsonl'  # 输出 JSONL 文件路径

merge_json_files(entry_file_path, response_file_path, output_file_path)
