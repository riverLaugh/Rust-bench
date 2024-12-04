import json
import openai
import csv
import os
from swebench import PatchManager

if __name__ == "__main__":

    input_file = "/home/riv3r/SWE-bench/swebench/collect/tasks/bitflags-task-instances.jsonl.all"
    output_file = "/home/riv3r/SWE-bench/swebench/collect/llmfilter/output.csv"
    output_file_all = "/home/riv3r/SWE-bench/swebench/collect/llmfilter/output.all.csv"
    output_json_file = "/home/riv3r/SWE-bench/swebench/collect/llmfilter/processed_instances.json"

    processed_instances = []

    with open(output_file, "w", newline="") as csvfile, open(output_file_all, "w", newline="") as csvfile_all:
        csv_writer = csv.writer(csvfile)
        csv_writer_all = csv.writer(csvfile_all)

        csv_writer.writerow(["Instance_id", "Test detected", "File Path"])
        csv_writer_all.writerow(["Instance_id", "Test detected", "File Path"])
        count = 0
        with open(input_file, "r") as file:
            for line in file:
                instance = json.loads(line.strip())
                patch = instance["patch"]
                patch_hunk = PatchManager(patch).hunks
                