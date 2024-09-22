#!/usr/bin/env bash

export OPENAI_API_KEY=sk-iA4HS8tiky1uILosB6Ad5fCbC5B347E0846e3cA4D59975B0

python -m swebench.inference.run_api\
 --dataset_name_or_path /root/ARiSE/SWEbench/SWE-bench/swebench/inference/base_datasets/SWE-bench__style-3__fs-oracle \
 --model_name_or_path gpt-3.5-turbo-1106 --output_dir ./outputs\
 --split train