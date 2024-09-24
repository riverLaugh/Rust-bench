#!/usr/bin/env bash

python -m swebench.inference.make_datasets.create_text_dataset \
    --dataset_name_or_path  /root/ARiSE/SWEbench/SWE-bench/swebench/inference/make_datasets/splited_datasets/serde\
     --prompt_style style-3 \
    --file_source oracle\
    --nname serde\
    --push_to_hub_user r1v3r