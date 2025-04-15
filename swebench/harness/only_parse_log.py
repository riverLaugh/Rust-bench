import os
import json
from pathlib import Path
from typing import Dict, List, Set
from swebench.harness.grading import get_logs_eval
import argparse

def collect_passed_instances(
    log_paths: Dict[str, Path],
    output_file: Path
) -> Dict[str, List[str]]:
    """
    从日志路径收集每种配置通过的实例 ID，计算所有配置均失败的 ID，保存结果。

    Args:
        log_paths: 配置名称到日志路径的映射
        output_file: 输出文件路径

    Returns:
        包含配置和通过/失败 ID 的字典
    """
    log_dict: Dict[str, List[str]] = {name: [] for name in log_paths}
    all_instances: Set[str] = set()

    for config_name, path in log_paths.items():
        path = Path(path)
        if not path.exists():
            print(f"Warning: Path {path} does not exist")
            continue

        for dir_name in path.iterdir():
            if not dir_name.is_dir():
                continue
            for instance_dir in dir_name.iterdir():
                if not instance_dir.is_dir():
                    continue
                instance_id = instance_dir.name
                all_instances.add(instance_id)

                test_output_path = instance_dir / "test_output.txt"
                log_file = instance_dir / "run_instance.log"

                if not test_output_path.exists():
                    continue

                try:
                    eval_sm, _ = get_logs_eval(log_file, test_output_path)
                    if any(status == "PASSED" for status in eval_sm.values()):
                        log_dict[config_name].append(instance_id)
                except Exception as e:
                    print(f"Error processing {instance_id} in {config_name}: {e}")

    # 计算所有配置均失败的实例
    passed_instances = set().union(*(log_dict[name] for name in log_paths))
    log_dict["all_failed"] = sorted(all_instances - passed_instances)

    # 保存结果为 JSON
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w") as f:
        json.dump(log_dict, f, indent=2)

    return log_dict

def main():
    parser = argparse.ArgumentParser(description="Collect passed and failed instance IDs from SWE-bench logs.")
    parser.add_argument(
        "--log-dir",
        type=str,
        default="/home/riv3r/SWE-bench/swebench/harness/logs/run_validation/top20_crates",
        help="Base directory for log files"
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default="log_dict.json",
        help="Output file path"
    )
    args = parser.parse_args()

    # 定义配置路径
    log_paths = {
        "default": Path(args.log_dir) / "default" / "gold",
        "nightly": Path(args.log_dir) / "nightly" / "gold",
        "test": Path(args.log_dir) / "test" / "gold",
        "nightly_wo_features": Path(args.log_dir) / "nightly_wo_features" / "gold",
    }

    # 收集并保存结果
    result = collect_passed_instances(log_paths, Path(args.output_file))
    print(f"Results saved to {args.output_file}")
    print(f"Summary: { {k: len(v) for k, v in result.items()} }")

if __name__ == "__main__":
    main()