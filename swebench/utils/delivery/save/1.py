import json

if __name__ == "__main__":
    with open("/home/riv3r/SWE-bench/swebench/utils/delivery/save/siada_case_example.jsonl", "r") as f:
        examples = [json.loads(line.strip()) for line in f]
    with open("/home/riv3r/SWE-bench/swebench/utils/delivery/save/siada_case_example.json", "w", encoding="utf-8") as f:
        json.dump(examples, f, indent=4, ensure_ascii=False)