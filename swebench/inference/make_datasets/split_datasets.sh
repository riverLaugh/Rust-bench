#!/usr/bin/env bash
python split_dataset.py \
--data_file /data/RustBench/SWE-bench/swebench/collect/tasks/serde-task-instances.jsonl \
--dataset_name serde \
--save_path /data/RustBench/SWE-bench/swebench/inference/make_datasets/splited_datasets