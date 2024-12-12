#!/usr/bin/env bash

# If you'd like to parallelize, do the following:
# * Create a .env file in this folder
# * Declare GITHUB_TOKENS=token1,token2,token3...

python get_tasks_pipeline.py \
    --repos 'asterinas/asterinas' \
    --path_prs '/Users/yjzhou/myworkspace/SWE-bench/swebench/collect/prs' \
    --path_tasks '/Users/yjzhou/myworkspace/SWE-bench/swebench/collect/tasks'\
