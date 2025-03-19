import os
import re
import json
import time
def analyse_validate_result(result_dir):
    result = {}  # 用于存储结果的字典

    for root, dirs, files in os.walk(result_dir):
        # 使用正则表达式匹配以数字结尾的路径
        if re.search(r"-\d+$", root):
            if "test_output.txt" not in files:
                build_log_path = os.path.join(root, "image_build_dir", "build_image.log")
                if os.path.exists(build_log_path):
                    with open(build_log_path, 'r') as f:
                        content = f.read()
                        # 捕获包含 error 或 warning 的行
                        error_lines = re.findall(r'.*error.*', content, re.IGNORECASE)
                        warning_lines = re.findall(r'.*warning.*', content, re.IGNORECASE)
                        
                        # 获取 root 的最后一层文件夹名称
                        last_folder = os.path.basename(root)
                        
                        # 将错误和警告信息存储到字典中
                        result[last_folder] = {
                            "errors": error_lines,
                            "warnings": warning_lines
                        }
                else:
                    # 如果 build_image.log 不存在，也记录到结果中
                    last_folder = os.path.basename(root)
                    result[last_folder] = {
                        "errors": ["no build_image.log"],
                        "warnings": []
                    }

    # 将结果转换为 JSON 格式并输出
    json_output = json.dumps(result, indent=4)
    print(json_output)
    return json_output


if __name__ == "__main__":
    json =  analyse_validate_result("/home/riv3r/SWE-bench/swebench/harness/logs/run_validation/hyper-index/gold")
    with open(f"analyse_validate_result_{time.strftime('%Y%m%d_%H%M%S')}.json", "w") as f:
        f.write(json)
