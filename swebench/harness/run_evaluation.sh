python run_evaluation.py \
    --dataset_name /root/ARiSE/SWEbench/SWE-bench/swebench/harness/results/bitflags_version_dataset_validated.all.json\
    --run_id run_bitflags_eval \
    --max_workers 1 \
    --cache_level env \
    --predictions_path gold\
    --force_rebuild True\
    --split test