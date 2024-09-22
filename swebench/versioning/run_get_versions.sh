# Example call for getting versions by building the repo locally
# python get_versions.py \
#     --path_tasks "<path to matplotlib task instances>" \
#     --retrieval_method build \
#     --conda_env "<name of conda environment to build task instances within>" \
#     --num_threads 10 \
#     --path_conda "<path to conda installation with `conda_env`>" \
#     --testbed "<path to folder>"

# Example call for getting versions from github web interface
python get_versions.py \
    --instances_path "/root/ARiSE/SWEbench/SWE-bench/swebench/collect/tasks/rustlings-task-instances.jsonl" \
    --retrieval_method github \
    --num_workers 1 \
    --output_dir "/root/ARiSE/SWEbench/SWE-bench/swebench/versioning/results"\
    --cleanup