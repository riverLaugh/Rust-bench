python run_evaluation.py \
    --dataset_name  r1v3r/SWE-bench_bitflags_style-3__fs-oracle\
    --run_id run_evaluation_bitflags \
    --max_workers 4 \
    --cache_level env \
    --predictions_path /root/ARiSE/SWEbench/SWE-bench/swebench/inference/outputs/gpt-4o-mini__SWE-bench_bitflags_style-3__fs-oracle__train.jsonl\
    --force_rebuild True\
    --split train