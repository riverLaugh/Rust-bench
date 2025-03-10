import json

with open("/data/RustBench/SWE-bench/swebench/utils/delivery/classification_results.json", "r") as f:
    data = json.load(f)

with open("classification_results_cn.json", "w") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)