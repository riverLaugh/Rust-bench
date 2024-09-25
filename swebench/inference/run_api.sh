#!/usr/bin/env bash

python -m swebench.inference.run_api\
 --dataset_name_or_path r1v3r/SWE-bench_serde_style-3__fs-oracle \
 --model_name_or_path gpt-4o-mini --output_dir ./outputs\
