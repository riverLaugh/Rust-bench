from datasets import Dataset, DatasetDict,load_dataset,concatenate_datasets
import os
a = [
    "BurntSushi__memchr-126",
    "BurntSushi__memchr-82",
    "bitflags__bitflags-282",
    "bitflags__bitflags-351",
    "cuviper__autocfg-56",
    "cuviper__autocfg-62",
    "rust-lang__libc-2100",
    "rust-lang__libc-2201",
    "rust-lang__libc-2215",
    "rust-lang__libc-2240",
    "rust-lang__libc-2304",
    "rust-lang__libc-2366",
    "rust-lang__libc-2606",
    "rust-lang__libc-2622",
    "rust-lang__libc-2828",
    "rust-lang__libc-3343",
    "rust-lang__libc-3483",
    "rust-lang__libc-3583",
    "rust-lang__libc-3604",
    "rust-lang__libc-3617",
    "rust-lang__libc-3690",
    "rust-lang__libc-3695",
    "rust-lang__libc-3745",
    "rust-lang__libc-3762",
    "rust-lang__libc-3843",
    "rust-lang__libc-3882",
    "rust-lang__libc-3885",
    "rust-lang__libc-3950",
    "rust-lang__libc-3952",
    "rust-lang__libc-3966",
    "rust-lang__libc-4033",
    "rust-lang__libc-4086",
    "rust-lang__libc-4091",
    "rust-random__getrandom-602",
    "rust-random__getrandom-614"
  ]

dataset = load_dataset("r1v3r/top20_crates", split="train")

dataset = dataset.filter(lambda x: x["instance_id"] in a)

dataset.push_to_hub("r1v3r/top20_crates_fail", token=os.getenv("HUGGING_FACE_HUB_TOKEN"))
