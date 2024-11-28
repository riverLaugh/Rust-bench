import csv
import json
import openai
from datasets import load_dataset
import os

# Set OpenAI API key
openai.api_key = os.environ.get("OPENAI_API_KEY")

# Function to read JSON data from a local file
def read_json_local(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"Failed to read JSON file: {e}")
        return None

# Analyze an instance using GPT API
def analyze_instance(instance, model="gpt-4o-mini-2024-07-18"):
    prompt = f"""
    Please analyze the following SWE-bench instance and output the following information as **concise labels only**:
    1. The type of bug (choose one: control flow error, calculation error, state management error, data handling error, resource mismanagement, concurrency issues, algorithm design flaws, boundary condition errors, timing or sequence errors, syntax error, runtime error, performance issue, security vulnerability, compatibility issue, etc.).
    2. The difficulty of fixing the bug (choose one: easy, moderate, hard). **Base your evaluation on the following factors**:
        - **Easy**: Issues within a single module, easy to reproduce, requiring minimal changes, and no specialized knowledge.
        - **Moderate**: Problems spanning multiple modules, necessitating some domain knowledge, with moderate and cautious modifications.
        - **Hard**: Involves underlying systems, concurrency issues, or extensive changes, requiring deep architectural understanding.
    3. Whether the patch is single-hunk or multi-hunk. A patch is single-hunk if it modifies a single continuous block of code; it is multi-hunk if it modifies multiple non-contiguous blocks of code.

    **Output format** (strictly follow this):
    - Bug Type: [comma-separated labels]
    - Difficulty: [single label]
    - Number of Hunks: [Number of Hunks]
    - Lines of Code(LOC) in the Patch: [Total number of lines added, removed, or modified in the patch.]
    - Function/Module Scope: [Number of functions or modules affected by the patch.]

    Instance Details:
    - Issue Description: {instance["problem_statement"]}
    - Comment: {instance["hints_text"]}
    - Code Patch:
    ```diff
    {instance["patch"]}
    """

    try:
        openai.base_url = "https://api5.xhub.chat/v1/"
        response = openai.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a software engineering expert specializing in bug classification and difficulty assessment."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        content = response.choices[0].message.content.strip()
        return content
    except Exception as e:
        print(f"Failed to call GPT API: {e}")
        return None

# Write results to CSV
def write_results_to_csv(results, output_file):
    header = ["instance_id", "bug_type", "difficulty", "number_of_hunks", "loc", "function_scope"]
    
    try:
        with open(output_file, mode='a', encoding='utf-8', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(header)
            writer.writerows(results)
        print(f"Results saved to {output_file}")
    except Exception as e:
        print(f"Failed to write CSV file: {e}")

def fetch_dataset_from_hf(dataset_name, split='train'):
    """从 Hugging Face 拉取数据集"""
    try:
        dataset = load_dataset(dataset_name, split=split)
        return dataset
    except Exception as e:
        print(f"从 Hugging Face 加载数据集失败: {e}")
        return None



# Main function
def main():
    # input_file = "/home/riv3r/SWE-bench/swebench/harness/results/asterinas_validated.json"
    # data = read_json_local(input_file)

    data = fetch_dataset_from_hf("r1v3r/bitflags_validated", "train")
    output_file = "analysis_results.csv"
    if not data:
        print("Data loading failed")
        return

    results = []
    print("Starting data analysis...")

    for instance in data:
        instance_id = instance.get("instance_id", "Unknown")
        analysis = analyze_instance(instance=instance)

        if analysis:
            try:
                # Extract results from the analysis response
                analysis_lines = analysis.split("\n")
                bug_type = analysis_lines[0].split(": ")[1]
                difficulty = analysis_lines[1].split(": ")[1]
                number_of_hunks = analysis_lines[2].split(": ")[1]
                loc = analysis_lines[3].split(": ")[1]
                function_scope = analysis_lines[4].split(": ")[1]

                # Append results for this instance
                results.append([instance_id, bug_type, difficulty, number_of_hunks, loc, function_scope])
            except Exception as e:
                print(f"Failed to parse analysis for instance {instance_id}: {e}")

    # Save results to CSV
    write_results_to_csv(results, output_file)

if __name__ == "__main__":
    main()
