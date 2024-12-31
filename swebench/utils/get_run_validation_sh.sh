#!/bin/bash

python get_run_validation_sh.py \
    --org 'r1v3r' \
    --repo 'proc-macro2-None-task-instances_versions' \
    --max_workers 4 \
    --cache_level env
