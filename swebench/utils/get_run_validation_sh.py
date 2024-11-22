import os
import argparse
from swebench.harness.constants import KEY_INSTANCE_ID
from swebench.harness.utils import load_swebench_dataset

ORG = "r1v3r"

def main(dataset_name: str):

    run_id = dataset_name.split("/")[1]

    results = {}
    for data in load_swebench_dataset(dataset_name, "train"):
        id = data[KEY_INSTANCE_ID]
        version = data["version"]
        if version not in results:
            results[version] = [id]
        else:
            results[version].append(id)
    results = {
        t[0]: t[1]
        for t in sorted(results.items(), key=lambda x: float(x[0]), reverse=True)
    }

    with open(os.path.join(os.path.dirname(__file__), "run_validation.sh"), "w") as fd:
        fd.write(f"#!/bin/bash\n\n")
        fd.write(f"# {dataset_name}\n\n")
        for version, ids in results.items():
            fd.write(f"# {version}\n")
            fd.write(f"# python run_validation.py \\\n")
            fd.write(f"#     --dataset_name {dataset_name} \\\n")
            fd.write(f"#     --run_id {run_id} \\\n")
            fd.write(f"#     --max_workers 1 \\\n")
            fd.write(f"#     --cache_level env \\\n")
            fd.write(f'#     --instance_ids {" ".join(ids)}\n')
            fd.write(f"\n")


if __name__ == "__main__":
    args = argparse.ArgumentParser()
    args.add_argument("--repo", type=str, required=True)
    args = args.parse_args()
    main(f"{ORG}/{args.repo}")
