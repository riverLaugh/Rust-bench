import json
import openai
import csv
import os
from swebench import PatchManager
import tiktoken
from collections import defaultdict
import time
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor, as_completed

# 定义模型的 token 价格（示例价格，请根据实际情况调整）
# 价格单位：美元，每千 tokens 的价格
INPUT_COSTS = {
    "gpt-4o-2024-08-06": 0.0000025
    # 添加其他模型的输入价格如果需要
}

OUTPUT_COSTS = {
    "gpt-4o-2024-08-06": 0.00001
    # 添加其他模型的输出价格如果需要
}

def count_tokens(text, model="gpt-4o-2024-08-06"):
    """
    使用 tiktoken 估算文本的 token 数量
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError as e:
        print(f"Encoding error: {e}")
        encoding = tiktoken.get_encoding("cl100k_base")  # 默认编码
    return len(encoding.encode(text))

def resolve_conflicts(responses):
    if not responses:
        return None  # 如果 responses 是空列表，返回 None
    response_counts = defaultdict(int)
    for res in responses:
        response_counts[res] += 1

    sorted_responses = sorted(response_counts.items(), key=lambda x: x[1], reverse=True)

    if sorted_responses[0][1] >= 2:
        return sorted_responses[0][0]
    elif len(sorted_responses) > 0:
        return sorted_responses[0][0]  # 返回第一个响应作为默认值
    else:
        return json.dumps({"test": False, "hunks": [], "explain": "Conflict resolution failed."})


def process_instance(instance, model_name, input_cost_per_1000, output_cost_per_1000):
    patch = instance["patch"]
    patch_hunk = PatchManager(patch).hunks
    patch_str = ""
    for i, hunk in enumerate(patch_hunk):
        patch_str += str(i) + "\n" + hunk + "\n"

    prompt = f"""
Analyze the following Rust diff from a GitHub Pull Request (PR) to determine if it involves test-related changes in the context of bug fixing. 
This PR is expected to be about bug fixing. A bug-fixing PR should contain both fix hunks and test hunks. Your task is to identify whether the PR is a bug-fixing one and, if so, which hunks are related to testing.
The PR may be not related to bug fixing (e.g., it adds new features or improves performance).

A hunk is considered test-related if it:
1. **Introduces or modifies test functions** (e.g., functions annotated with `#[test]`).
2. **Modifies files or modules associated with testing** (e.g., located within `tests` directories or file paths containing 'test', 'e2e', or 'testing').
3. **Adds or modifies assertions, mocks, or test utilities**.

Here is the Rust diff:

<patch>
{patch}
</patch>

Respond with **only** a JSON object adhering to the following structure:

{{
    "test": true or false,
    "hunks": [<hunk_number1>, <hunk_number2>, ...],
    "explain": "<explanation of your decision>"
}}

**Guidelines:**
- **"test"** (`bool`): Indicates whether the PR involves test-related changes.
  - `true`: The PR includes test-related changes.
  - `false`: The PR does not include test-related changes.
  
- **"hunks"** (`array of integers`): List of hunk numbers (0-indexed) that are related to testing.
  - If `"test": true`, provide the relevant hunk numbers.
  - If `"test": false`, this should be an empty array `[]`.

- **"explain"** (`string`): Explanation of the decision. Describe how you identified test-related changes in the PR.

**Constraints:**
- **Respond with only the JSON object.**
- **No additional text** or explanations should be included outside of the JSON.

**Examples:**

1. **PR with Test-Related Changes:**

{{
    "test": true,
    "hunks": [0, 2],
    "explain": "Hunk 0 introduces a new test function, and hunk 2 modifies existing test utilities."
}}

2. **PR without Test-Related Changes:**

{{
    "test": false,
    "hunks": [],
    "explain": "This pr is abour adding new features."
}}

    """

    openai.api_key = os.environ.get("OPENAI_API_KEY")
    openai.base_url = "https://api5.xhub.chat/v1/"

    # 估算 prompt 的 token 数量
    prompt_tokens = count_tokens(prompt, model=model_name)

    responses = []
    total_output_tokens = 0
    total_cost = 0.0
    final_response = None
    try:

        # 进行三次采样
        for _ in range(3):
            response = openai.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant proficient in Rust development."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                response_format= {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "response",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "test": {"type": "boolean"},
                                "hunks": {"type": "array", "items": {"type": "integer"}},
                                "explain": {"type": "string"}
                            }
                        }
                    }
                }
            )
            # 获取 response 内容
            content = response.choices[0].message.content.strip()
            responses.append(content)
            print(content)
            # 估算 response 的 token 数量
            response_tokens = count_tokens(content, model=model_name)

            # 累加 tokens 和费用
            total_output_tokens += response_tokens
            total_cost += (response_tokens * output_cost_per_1000)

        # 累加 prompt tokens 和费用（每一采样都用同一个 prompt）
        total_cost += (prompt_tokens * input_cost_per_1000)

        # 解析并合并三个响应
        final_response = resolve_conflicts(responses)

        # 解析响应内容
        try:
            response_json = json.loads(final_response)
            test_detected = response_json.get("test", False)
            hunks_related = response_json.get("hunks", [])
            explanation = response_json.get("explain", "none")
        except json.JSONDecodeError:
            print(f"JSON decode error for instance {instance['instance_id']}: {final_response}")
            test_detected = False
            hunks_related = []
            explanation = "Invalid JSON response."

        if test_detected:
            # 填充 hunks
            test_hunks = []
            fix_hunks = []
            try:
                # 解析 hunk numbers
                hunk_numbers = hunks_related

                for i, hunk in enumerate(patch_hunk):
                    if i in hunk_numbers:
                        test_hunks.append(hunk)
                    else:
                        fix_hunks.append(hunk)

                instance["test_patch"] = "\n".join(test_hunks) if test_hunks else ""
                instance["patch"] = "\n".join(fix_hunks) if fix_hunks else ""
            except Exception as e:
                print(f"Error processing hunks for instance {instance['instance_id']}: {e}")
                instance["test_patch"] = ""
                instance["patch"] = ""
        else:
            instance["test_patch"] = ""
    except Exception as e:
        print(f"Error processing instance {instance['instance_id']}: {e}")
        if final_response is None:
            final_response = json.dumps({"test": False, "hunks": [], "explain": str(e)})
        print(responses)
    
    return instance, total_cost, total_output_tokens, final_response

def main(args):
    start_time = time.time()
    input_file = args.file_path

    # 提取文件名并生成其他文件名
    input_filename = input_file.split("/")[-1].split("-")[0]  # 提取文件名部分
    output_file = f"/home/riv3r/SWE-bench/swebench/collect/llmfilter/{input_filename}_output.json"
    output_file_all = f"/home/riv3r/SWE-bench/swebench/collect/llmfilter/{input_filename}_output.all.json"
    output_json_file = f"/home/riv3r/SWE-bench/swebench/collect/llmfilter/{input_filename}_llm.json"


    processed_instances = []
    response_json_list = []
    # 初始化计费相关变量
    total_input_tokens = 0
    total_output_tokens = 0
    total_cost = 0.0

    # 获取模型的成本
    model_name = "gpt-4o-2024-08-06"
    input_cost_per_1000 = INPUT_COSTS.get(model_name, 0.03)   # 默认输入价格
    output_cost_per_1000 = OUTPUT_COSTS.get(model_name, 0.03) # 默认输出价格

    with open(output_file, "w", newline="") as output_json, open(output_file_all, "w", newline="") as all_json, open(input_file, "r") as file:
        instances = [json.loads(line.strip()) for line in file]
        complete = 0
        # 使用 ThreadPoolExecutor 实现多线程
        with ThreadPoolExecutor(max_workers=10) as executor:  # 你可以调整 max_workers 的数量
            futures = {executor.submit(process_instance, instance, model_name, input_cost_per_1000, output_cost_per_1000): instance for instance in instances}
            for future in as_completed(futures):
                instance_result, cost, output_tokens,final_response = future.result()
                if instance_result["test_patch"] != "":
                    processed_instances.append(instance_result)
                if final_response  is not None:
                    response_json = json.loads(final_response)
                    response_json["instance_id"] = instance_result["instance_id"]
                    response_json_list.append(response_json)
                complete += 1
                print(f"Processed instances:{len(processed_instances)}, completed:{complete}")
                total_output_tokens += output_tokens
                total_cost += cost

        end_time = time.time()
        duration = end_time - start_time

        # 保存处理后的实例为 JSON 文件
        json.dump(processed_instances, output_json, indent=4)
        json.dump(response_json_list, all_json, indent=4)

        # 输出总计费信息
        print(f"Results saved to {output_file}, {output_file_all}, and {output_json_file}")
        print(f"Total input tokens used: {total_input_tokens}")
        print(f"Total output tokens used: {total_output_tokens}")
        print(f"Total cost: ${total_cost:.4f}")
        print(f"Total runtime: {duration:.2f} seconds")  # 打印运行时间

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--file_path", default="princeton-nlp/SWE-bench_Lite", type=str, help="path to JSON file.")
    args = parser.parse_args()
    main(args=args)
    