python run_evaluation.py \
    --dataset_name r1v3r/bitflags_validated\
    --run_id run_bitflags_eval \
    --max_workers 1 \
    --cache_level instance \
    --predictions_path /root/ARiSE/SWEbench/SWE-bench/swebench/inference/outputs/gpt-4o-2024-08-06__SWE-bench_bitflags_style-3__fs-oracle__train.jsonl\
    --force_rebuild True\
    --split train