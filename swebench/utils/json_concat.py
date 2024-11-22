import json

# 定义文件路径
file1_path = "/home/riv3r/SWE-bench/swebench/harness/results/arrow-rs_validated-45.0.json"
file2_path = "/home/riv3r/SWE-bench/swebench/harness/results/arrow-rs_validated-50.0.json"
output_path = "./arrow-rs.json"

# 加载 JSON 文件
with open(file1_path, "r") as file1, open(file2_path, "r") as file2:
    json1 = json.load(file1)
    json2 = json.load(file2)

# 合并 JSON
merged_json = json1 + json2

# 写入合并后的 JSON 到文件
with open(output_path, "w") as output_file:
    json.dump(merged_json, output_file, indent=4, ensure_ascii=False)

print(f"合并后的 JSON 文件已保存到 {output_path}")
