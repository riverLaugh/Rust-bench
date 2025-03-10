#!/bin/bash

python build_dataset_ft.py \
    --instances_path "/data/RustBench/SWE-bench/swebench/collect/tasks/serde-task-instances.jsonl" \
    --output_path "/data/RustBench/SWE-bench/swebench/collect/ft_datasets" \
    --eval_path "<path to folder containing all evaluation task instances>"