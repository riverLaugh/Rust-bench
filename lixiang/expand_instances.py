import argparse
import os
import json
import random
from datasets import load_dataset
import openai
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from transfer_dataset import main as make_code_snippet


openai_api = os.getenv("OPENAI_API_KEY")
openai.api_key = openai_api
openai.base_url = "https://api5.xhub.chat/v1/"


def run_inference(instance, model="gpt-4o-2024-08-06") ->list:
    """
    使用 OpenAI API 获取问题类型和等级判定原因。
    
    Args:
        problem_statement (str): 问题陈述。
        openai_api_key (str): OpenAI API 密钥。
        model (str): 使用的模型名称。
    
    Returns:
        tuple: (problem_type, severity_level, reason)
    """

    system_messages = "您是一位资深的 Rust 程序专家，擅长分析 Rust 代码中的潜在问题，并提供详细的分类和评估。"

    prompt = (
    f"{system_messages}\n\n"
    f"请根据以下信息完成分析：\n"
    f"1. 需要评估的代码片段：\n"
    f"   ```{instance['code_snippet']}```\n\n"
    f"2. 问题描述（可能存在偏差）：\n"
    f"   ```{instance['bug_report']}```\n\n"
    f"3. 问题触发测试：\n"
    f"   ```{instance['test_patch']}```\n\n"
    f"请按照以下要求完成分析，所有回答用中文且符合格式限制：\n\n"

    f"**第一步：问题类型分类（problem_type）**\n"
    f"- 根据代码和问题描述，确定问题的核心类型。\n"
    f"- 类型名称需简洁（≤10汉字），可选类型包括：\n"
    f"  逻辑错误、性能问题、安全漏洞、资源泄漏、代码冗余、异常处理缺失等。\n"
    f"- 若现有类型不适用，需根据问题本质定义新类型。\n\n"

    f"**第二步：案例价值评估（level）**\n"
    f"- 判断案例的价值级别为 'low' 或 'high'：\n"
    f"  - 'high'：问题描述清楚地展现了该段代码的问题，并且这个问题是重要的。\n"
    f"  - 'low'：问题描述没有正确描述该段代码的问题，或者这个问题是微不足道的。\n"
    f"- 需结合代码行为、潜在影响及问题描述的合理性进行判断。\n\n"

    f"**第三步：评估理由（level_reason）**\n"
    f"- 请用 200-300 字的中文说明理由，需包含以下内容：\n"
    f"  1. **代码分析**：指出具体代码行的潜在问题。\n"
    f"  2. **逻辑推导**：解释问题是否会导致描述中的风险（如未处理异常）。\n"
    f"  3. **影响评估**：描述问题可能导致的后果及严重性。\n"
    f"  4. **判定依据**：基于代码逻辑或行业最佳实践解释级别选择原因。\n"
    f"- 禁止直接提及 'bug report' 或 'ground truth'，需基于代码本身分析。\n\n"

    f"**输出格式要求**：\n"
    f"必须严格返回以下 JSON 格式，键名单行且无换行：\n"
    f"{{\n"
    f"  \"problem_type\": \"填写类型名称\",\n"
    f"  \"level\": \"low/high\",\n"
    f"  \"level_reason\": \"详细理由文本\"\n"
    f"}}\n"
    f"注：所有字段必须填写，且需符合上述要求。"
    )

    # 调用 OpenAI API
    try:
        response = openai.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_messages},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "response",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "problem_type": {"type": "string"},
                            "level": {"type": "string"},
                            "level_reason": {"type": "string"}
                        },
                        "required": ["problem_type", "level", "level_reason"]
                    }
                }
            }
        )
        content = response.choices[0].message.content.strip()
        response_json = json.loads(content)
        print(f"OpenAI API response: {response_json}")
        instance["problem_type"] = response_json["problem_type"]
        instance["level"] = response_json["level"]
        instance["level_reason"] = response_json["level_reason"]
        return instance
    except Exception as e:
        print(f"OpenAI API error: {e}")
        instance["problem_type"] = "Unknown"
        instance["level"] = "Unknown"
        instance["level_reason"] = "Unknown"
        return instance


def generate_bug_report(instance,model="gpt-4o-2024-08-06") -> list:
    """
    处理单个示例，调用 OpenAI API 进行分类。
    
    Args:
        instance (dict): 数据集中的单个示例。
        openai_api (str): OpenAI API 密钥。
    
    Returns:
        dict: 包含分类结果的字典。
    """
    res = []


    response = openai.chat.completions.create(
        model=model,
        messages=[
            {"role":"system","content":"您是一位资深的 Rust 程序专家，擅长分析 Rust 代码中的潜在问题"},
            {"role":"user","content":instance["text"]},
        ],
        temperature=0.9
    )
    content = response.choices[0].message.content.strip()

    review_response = openai.chat.completions.create(
        model=model,
        messages=[
            {"role":"system","content":"您是一位资深的程序员，擅长中文和英文的代码审查。"},
            {"role":"user","content":"请你分析下面这段错误报告：如果包含乱码，请去掉乱码；如果主要内容为英文, 请将内容翻译为中文\n"+ content},
        ],
        temperature=0.8
    )
    review_content = review_response.choices[0].message.content.strip()
    instance["bug_report"] = review_content
    print(f"Generated bug report: {review_content}")
    res.append(instance)
    return res


def create_bug_report_task(dataset, range_num):
    res = []
    for i in range(range_num):
        for sample in dataset:
            code_snippet = sample["code_snippet"]
            test_patch = sample["test_patch"]
            if random.random() < 0.3:
                sample["text"] = f"请根据以下代码片段和触发测试，生成一个错误报告：\n\n{code_snippet}\n\n触发测试：{test_patch}"
            else:
                sample["text"] = f"请根据以下代码片段，生成一个错误报告：\n\n{code_snippet}\n\n"
            res.append(sample)
    return res
    

def make_code_snippet_task(dataset_name_or_path, split):
    return make_code_snippet(
        dataset_name_or_path,
        split=split,
        output=None  # 根据实际需求调整参数
    )


def main(dataset_name_or_path: str,split:str, num_samples: int, output_dir: str):
    # 加载数据集
    os.makedirs(output_dir, exist_ok=True)
        # 定义 JSON 文件路径
    dataset_json = []
    for sample in load_dataset(dataset_name_or_path, split=split):
        dataset_json.append(sample)
    dataset_name = dataset_name_or_path.split("/")[-1]
    dataset_dir = os.path.join(output_dir, dataset_name)
    os.makedirs(dataset_dir, exist_ok=True)  # 创建子目录，如果不存在
    dataset_path = os.path.join(dataset_dir, "dataset.json")
    code_entries_path = os.path.join(dataset_dir, "code_entries.json")
    if os.path.exists(code_entries_path):
        print("Loading existing code entries...")
        with open(code_entries_path, "r", encoding="utf-8") as f:
            code_entries = json.load(f)
    else:
        print("Creating code entries...")
        code_entries = make_code_snippet_task(dataset_name_or_path, split)
        with open(code_entries_path, "w", encoding="utf-8") as f:
            json.dump(code_entries, f, ensure_ascii=False, indent=4)

    #将code与dataset合并
    for entry in code_entries:
        for sample in dataset_json:
            if entry["instance_id"] == sample["instance_id"]:
                sample["code_snippet"] = entry["code_snippet"]

    if os.path.exists(dataset_path):
        print("Loading existing dataset...")
        with open(dataset_path, "r", encoding="utf-8") as f:
            dataset = json.load(f)
    else:
        print("Creating dataset...")
        dataset = create_bug_report_task(dataset_json, num_samples)
        with open(dataset_path, "w", encoding="utf-8") as f:
            json.dump(dataset, f, ensure_ascii=False, indent=4)
    bug_report_dataset = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(generate_bug_report ,instance, "gpt-4o-2024-08-06") for instance in dataset]

        for future in tqdm(as_completed(futures), total=len(futures), desc="Processing"):
            try:
                result = future.result()
                bug_report_dataset.extend(result)
            except Exception as e:
                print(f"Error processing example: {e}")

    
    #在bug report dataset的基础上添加code snippet
    final_dataset = bug_report_dataset
    res = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(run_inference, sample ) for sample in final_dataset]

        for future in tqdm(as_completed(futures), total=len(futures), desc="Processing"):
            try:
                result = future.result()
                res.append(result)
            except Exception as e:
                print(f"Error processing example: {e}")
    output_file = os.path.join(output_dir, "res.jsonl")
    code_entry_dict = {entry["instance_id"]: entry for entry in code_entries}

    with open(output_file, 'w', encoding='utf-8') as f:
        for r in res:
            code_entry = code_entry_dict.get(r["instance_id"])
            if code_entry:
                merged_json = {
                    "code_snippet": r["code_snippet"],
                    "target_function": code_entry.get("target_function", ""),
                    "review_type": code_entry.get("review_type", ""),
                    "issue_detail": {
                        "problem_type": r["problem_type"],
                        "location": code_entry.get("issue_detail", {}).get("location", ""),
                        "level": r["level"],
                        "description": r["bug_report"],
                        "level_reason": r["level_reason"]
                    },
                    "repo": code_entry.get("repo", ""),
                    "branch": code_entry.get("branch", ""),
                    "file_path": code_entry.get("file_path", ""),
                    "language": code_entry.get("language", "")
                }
                f.write(json.dumps(merged_json, ensure_ascii=False) + '\n')
#     # 读取原始数据集文件并写入输出文件
    with open("/data/RustBench/SWE-bench/lixiang/asserts/siada_edu_case.jsonl",'r',encoding='utf-8') as f ,open(output_file,'a',encoding='utf-8') as f2:
        lines = f.readlines()
        for line in lines:
            line = line.strip()
            if line:
                f2.write(line + '\n')
        


if __name__ == "__main__":
    # 获取脚本所在目录的绝对路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # 设置默认输出目录为脚本目录下的 "output" 文件夹
    default_output_dir = os.path.join(script_dir, "output")
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset_name_or_path", type=str, default="r1v3r/RustGPT_Bench_100", help="Dataset name or path")
    parser.add_argument("--num_samples", type=int, default=4, help="拓展几倍的数据")
    parser.add_argument("--split", type=str, default="train", help="Split to use")
    parser.add_argument("--output_dir", type=str, default=default_output_dir, help="Output directory")    
    main(**vars(parser.parse_args()))