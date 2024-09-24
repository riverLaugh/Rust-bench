#!/usr/bin/env bash
python split_dataset.py \
--data_file /root/ARiSE/SWEbench/SWE-bench/swebench/collect/tasks/serde-task-instances.jsonl \
--dataset_name serde \
--save_path /root/ARiSE/SWEbench/SWE-bench/swebench/inference/make_datasets/splited_datasets