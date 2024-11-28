#!/usr/bin/env bash

python -m swebench.inference.make_datasets.create_text_dataset \
    --dataset_name_or_path  r1v3r/asterinas_validated\
     --prompt_style bug_report\
    --file_source oracle\
    --nname asterinas\
    --split train\
    --push_to_hub_user r1v3r