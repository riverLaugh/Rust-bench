python run_evaluation.py \
    --dataset_name princeton-nlp/SWE-bench_Lite\
    --run_id run_swe_evaluation_lite \
    --max_workers 4 \
    --cache_level env \
    --predictions_path gold\
    --force_rebuild True\
    --split test