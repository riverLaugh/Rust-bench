# 加载数据集
from datasets import load_dataset
import json

dataset_dict = load_dataset("princeton-nlp/SWE-bench_Lite")

# 查看 dev 分割的前几条记录
dataset_dict.load_from_disk('SWE-bench_Lite')

# 查看 test 分割的前几条记录
# Save the first record of the 'test' split to a local file
with open('/root/ARiSE/SWEbench/SWE-bench/test_record.json', 'w') as f:
    json.dump(dataset_dict['test'][0], f)
