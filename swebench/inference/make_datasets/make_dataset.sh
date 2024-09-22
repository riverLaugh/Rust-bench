#!/usr/bin/env bash

python -m swebench.inference.make_datasets.create_text_dataset \
    --dataset_name_or_path  /root/ARiSE/SWEbench/SWE-bench/swebench/collect/tasks/rustlings-task-instances.jsonl\
    --output_dir ../base_datasets --prompt_style style-3 \
    --file_source oracle\
    --splits train\
    --validation_ratio 0