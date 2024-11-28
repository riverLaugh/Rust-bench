#!/usr/bin/env bash

python -m swebench.inference.make_datasets.create_text_dataset \
    --dataset_name_or_path  r1v3r/bitflags\
     --prompt_style style-3 \
    --file_source oracle\
    --nname asterinas\
    --split train\
    --push_to_hub_user r1v3r