import re
import json

# 定义日志文件路径
log_file_path = 'process.log'  # 请将 'process.log' 替换为你的实际日志文件路径

# 定义正则表达式来解析日志
processing_pattern = re.compile(r"Processing: (\S+)")
error_pattern = re.compile(r"ERROR - Error running (\S+\.py) for (\S+):")

# 初始化结果字典
tasks_status = {}  # 用于记录每个任务的状态
errors_scripts = {  # 用于记录每个脚本的错误任务
    "run_validation.py": [],
    "environment_setup_commit.py": [],
    "get_versions.py": []
}

# 读取日志文件并解析
with open(log_file_path, 'r', encoding='utf-8') as log_file:
    for line in log_file:
        # 检测正在处理的任务
        processing_match = processing_pattern.search(line)
        if processing_match:
            task = processing_match.group(1)
            tasks_status[task] = 'success'  # 假设任务成功，后面根据错误信息更新状态
            continue  # 继续读取下一行

        # 检测错误任务
        error_match = error_pattern.search(line)
        if error_match:
            script, task = error_match.groups()
            tasks_status[task] = 'error'  # 将任务状态更新为错误
            # 将任务添加到对应的脚本错误列表中
            if script in errors_scripts:
                errors_scripts[script].append(task)
            else:
                # 如果脚本名称不在预定义的错误脚本中，可以选择添加或忽略
                errors_scripts[script] = [task]

# 将结果整理为所需的 JSON 格式
result = {
    "success": [task for task, status in tasks_status.items() if status == 'success'],
    "errors": errors_scripts
}

# 输出结果为 JSON 格式
output_json = json.dumps(result, indent=4, ensure_ascii=False)
print(output_json)

# 将 JSON 结果写入文件（可选）
with open('output.json', 'w', encoding='utf-8') as output_file:
    output_file.write(output_json)
