import json
import openai
import csv
import os
from swebench import PatchManager
import tiktoken
from collections import defaultdict
import time

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
    """
    通过多数投票法解决冲突。如果有两次以上的响应相同，则返回一致的结果。
    如果三次结果全不相同，则返回 "conflict" 及所有响应。
    """
    response_counts = defaultdict(int)
    for res in responses:
        response_counts[res] += 1
    
    # 查找出现次数最多的响应
    sorted_responses = sorted(response_counts.items(), key=lambda x: x[1], reverse=True)
    
    if len(sorted_responses) == 0:
        return "false, none"  # 无响应时默认
    
    # 如果多数响应相同
    if sorted_responses[0][1] >= 2:
        return sorted_responses[0][0]
    else:
        for res in responses:
            if res.strip().lower().startswith("true"):
                return res

if __name__ == "__main__":
    start_time = time.time()
    input_file = "/home/riv3r/SWE-bench/swebench/collect/tasks/bitflags-task-instances.jsonl.all"
    output_file = "/home/riv3r/SWE-bench/swebench/collect/llmfilter/output.csv"
    output_file_all = "/home/riv3r/SWE-bench/swebench/collect/llmfilter/output.all.csv"
    output_json_file = "/home/riv3r/SWE-bench/swebench/collect/llmfilter/processed_instances.json"

    processed_instances = []

    # 初始化计费相关变量
    total_input_tokens = 0
    total_output_tokens = 0
    total_cost = 0.0

    # 获取模型的成本
    model_name = "gpt-4o-2024-08-06"
    input_cost_per_1000 = INPUT_COSTS.get(model_name, 0.03)   # 默认输入价格
    output_cost_per_1000 = OUTPUT_COSTS.get(model_name, 0.03) # 默认输出价格
    count = 0
    conflict_count = 0

    with open(output_file, "w", newline="") as csvfile, open(output_file_all, "w", newline="") as csvfile_all:
        csv_writer = csv.writer(csvfile)
        csv_writer_all = csv.writer(csvfile_all)

        csv_writer.writerow(["Instance_id", "Test detected", "File Path"])
        csv_writer_all.writerow(["Instance_id", "Test detected", "File Path"])

        with open(input_file, "r") as file:
            for line in file:
                instance = json.loads(line.strip())
                patch = instance["patch"]
                patch_hunk = PatchManager(patch).hunks
                patch_str = ""
                for i, hunk in enumerate(patch_hunk):
                    patch_str += str(i) + "\n" + hunk + "\n"

                prompt = f"""
                Analyze the following Rust diff from a GitHub Pull Request (PR) to determine if it involves test-related changes in the context of bug fixing. This PR is expected to be about bug fixing. If the PR is not related to bug fixing (e.g., it adds new features or improves performance), please return `"false, none"`.

                A bug-fixing PR should contain both fix hunks and test hunks. Your task is to identify whether the PR is a bug-fixing one and, if so, which hunks are related to testing.

                A hunk is considered test-related if it:
                1. **Introduces or modifies test functions** (e.g., functions annotated with `#[test]`).
                2. **Modifies files or modules associated with testing** (e.g., located within `tests` directories or file paths containing 'test', 'e2e', or 'testing').
                3. **Adds or modifies assertions, mocks, or test utilities**.

                Here is the Rust diff:
            
                <patch>
                {patch_str}
                <patch>

                Respond with **only** one of the following formats, without any additional text or explanations:
                - `"true, <hunk numbers separated by space>"` if the PR is about bug fixing and contains test-related changes. (Hunk numbers are 0-indexed.)
                - `"false, none"` if the PR is not about bug fixing or does not contain any test-related changes.
                """

                openai.api_key = os.environ.get("OPENAI_API_KEY")
                openai.base_url = "https://api5.xhub.chat/v1/"

                # 估算 prompt 的 token 数量
                prompt_tokens = count_tokens(prompt, model=model_name)

                responses = []
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
                        )
                        count += 1

                        # 获取 response 内容
                        content = response.choices[0].message.content.strip()
                        responses.append(content)
                        print(f"{count}-response: {content}")

                        # 估算 response 的 token 数量
                        response_tokens = count_tokens(content, model=model_name)

                        # 累加 tokens 和费用
                        total_output_tokens += response_tokens
                        total_cost += (response_tokens * output_cost_per_1000)

                    # 累加 prompt tokens 和费用（每一采样都用同一个 prompt）
                    total_input_tokens += prompt_tokens
                    total_cost += (prompt_tokens * input_cost_per_1000)

                    # 解析并合并三个响应
                    final_response = resolve_conflicts(responses)

                    # 打印合并后的响应
                    print(f"final response:{final_response}")
                    array = final_response.split(",")

                    # 解析响应内容
                    test_detected = array[0].strip().lower()
                    test_hunk_numbers = array[1].strip() if len(array) > 1 else "none"

                    # 如果存在冲突，记录冲突次数
                    if test_detected == "conflict":
                        conflict_count += 1

                    csv_writer_all.writerow([instance["instance_id"], final_response])

                    test_hunks = []
                    fix_hunks = []
                    if test_detected == "true":
                        csv_writer.writerow([instance["instance_id"], "true", test_hunk_numbers])

                        # 解析 hunk numbers
                        hunk_numbers = [int(num.strip()) for num in test_hunk_numbers.split(" ") if num.strip().isdigit()]

                        for i, hunk in enumerate(patch_hunk):
                            if i in hunk_numbers:
                                test_hunks.append(hunk)
                            else:
                                fix_hunks.append(hunk)
                        # 如果有一个patch为空则跳过
                        if not fix_hunks or not test_hunks:
                            continue
                        instance["test_patch"] = "\n".join(test_hunks) if test_hunks else ""
                        instance["patch"] = "\n".join(fix_hunks) if fix_hunks else ""
                        processed_instances.append(instance)
                        break
                    else:
                        instance["test_patch"] = ""
                    

                except Exception as e:
                    print(f"Error processing instance {instance['instance_id']}: {e}")

        
        end_time = time.time()
        duration = end_time - start_time

        # 保存处理后的实例为 JSON 文件
        with open(output_json_file, "w") as json_out:
            json.dump(processed_instances, json_out, indent=4)

        # 输出总计费信息
        print(f"Results saved to {output_file}, {output_file_all}, and {output_json_file}")
        print(f"Total input tokens used: {total_input_tokens}")
        print(f"Total output tokens used: {total_output_tokens}")
        print(f"Total cost: ${total_cost:.4f}")
        print(f"Total API calls: {count}")
        print(f"Total conflicts detected: {conflict_count}")
        print(f"Total runtime: {duration:.2f} seconds")  # 打印运行时间

