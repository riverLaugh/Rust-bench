#!/usr/bin/env bash

# If you'd like to parallelize, do the following:
# * Create a .env file in this folder
# * Declare GITHUB_TOKENS=token1,token2,token3...

python get_tasks_pipeline.py \
    --repos 'apache/arrow-rs' \
    --path_prs '/data/RustBench/SWE-bench/swebench/collect/prs' \
    --path_tasks '/data/RustBench/SWE-bench/swebench/collect/tasks'\
    --mode new
