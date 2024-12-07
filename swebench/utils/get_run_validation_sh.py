import argparse
import os

from swebench.harness.constants import KEY_INSTANCE_ID
from swebench.harness.utils import load_swebench_dataset


def main(args):
    org, repo, dataset_name, run_id, max_workers, cache_level = args.org, args.repo, f"{args.org}/{args.repo}", args.repo, args.max_workers, args.cache_level

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

    with open(os.path.join(os.path.dirname(__file__), f"{repo}_run_validation.sh"), "w") as fd:
        fd.write(f"#!/bin/bash\n\n")
        fd.write(f"# {dataset_name}\n\n")
        for version, ids in results.items():
            fd.write(f"# {version}\n")
            fd.write(f"# python run_validation.py \\\n")
            fd.write(f"#     --dataset_name {dataset_name} \\\n")
            fd.write(f"#     --run_id {run_id} \\\n")
            fd.write(f"#     --max_workers {max_workers} \\\n")
            fd.write(f"#     --cache_level {cache_level} \\\n")
            fd.write(f'#     --instance_ids {" ".join(ids)}\n')
            fd.write(f"\n")


if __name__ == "__main__":
    args = argparse.ArgumentParser()
    args.add_argument("--repo", type=str, required=True)
    args.add_argument("--org", type=str, default="r1v3r")
    args.add_argument(
        "--cache_level",
        type=str,
        choices=["none", "base", "env", "instance"],
        default="env",
    )
    args.add_argument("--max_workers", type=int, default=1)
    main(args.parse_args())
