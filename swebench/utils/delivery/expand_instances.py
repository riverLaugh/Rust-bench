import argparse
import os
import json
import re
from datasets import load_dataset,Dataset
from numpy import var
import openai
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from swebench import inference
from swebench.inference.make_datasets.create_text_dataset import main as create_text_dataset
from swebench.utils.delivery.transfer_dataset import main as make_code_snippet
from swebench.inference.make_datasets.utils import AutoContextManager
from tempfile import TemporaryDirectory
from swebench.inference.make_datasets.utils import AutoContextManager, ingest_directory_contents

def run_inference(instance, openai_api_key, model="gpt-4o-2024-08-06") ->list:
    """
    使用 OpenAI API 获取问题类型和等级判定原因。
    
    Args:
        problem_statement (str): 问题陈述。
        openai_api_key (str): OpenAI API 密钥。
        model (str): 使用的模型名称。
    
    Returns:
        tuple: (problem_type, severity_level, reason)
    """

    system_messages = "您是一位资深的 Rust 程序专家，擅长分析 Rust 代码中的潜在问题，并提供详细的分类和评估。您的任务是根据模型生成的 bug report、相关代码片段和正确的评估（ground truth），对问题进行分类、评估其级别并提供理由。"

    prompt = (
        f"{system_messages}\n\n"
        f"以下是模型生成的 bug report（注意：此报告不一定正确）：\n"
        f"\"{instance["bug_report"]}\"\n\n"
        f"以下是相关代码片段：\n"
        f"\"{instance["code_snippet"]}\"\n\n"
        f"以下是正确的评估（ground truth）：\n"
        f"\"{instance["problem_statement"]}\"\n\n"
        f"请按照以下步骤完成任务，所有回答使用中文并严格遵守字数限制：\n\n"
        f"1. **分类问题类型（problem_type）**：\n"
        f"   - 将 bug report 指出的问题分类为一个类型，类型名称简洁且不超过十个汉字。\n"
        f"   - 常见类型包括：逻辑错误、性能问题、安全漏洞、代码风格问题等。\n"
        f"   - 若现有类型不适用，可根据具体情况定义新类型。\n"
        f"   - 分类时，请对比 bug report 和 ground truth 的差异。\n\n"
        f"2. **评估级别（level）**：\n"
        f"   - 评估 bug report 的级别为 'low' 或 'high'：\n"
        f"     - 'low'：低价值问题，例如 bug report 错误或问题微不足道，建议降低类似问题的优先级。\n"
        f"     - 'high'：高价值问题，例如 bug report 正确且问题严重（如程序崩溃或安全漏洞），需用户关注。\n"
        f"   - 请对比 bug report 和 ground truth，根据差异选择级别。\n\n"
        f"3. **提供评估理由（level_reason）**：\n"
        f"   - 提供详细理由，不超过 300 字。\n"
        f"   - 包括代码分析、问题潜在影响及选择级别的依据，辅以相关代码示例。\n\n"
        f"请以以下 JSON 格式返回结果，确保键名是单行字符串，不含换行符：\n"
        f"{{\n"
        f"  \"problem_type\": \"...\",\n"
        f"  \"level\": \"...\",\n"
        f"  \"level_reason\": \"...\"\n"
        f"}}"
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
        return {
            "problem_type": "Unknown",
            "level": "Unknown",
            "level_reason": "Unknown"
        }


def generate_bug_report(num_samples,instance, openai_api,model) -> list:
    """
    处理单个示例，调用 OpenAI API 进行分类。
    
    Args:
        instance (dict): 数据集中的单个示例。
        openai_api (str): OpenAI API 密钥。
    
    Returns:
        dict: 包含分类结果的字典。
    """
    res = []
    openai.api_key = openai_api
    openai.base_url = "https://api5.xhub.chat/v1/"

    for i in range(num_samples):
        response = openai.chat.completions.create(
            model=model,
            messages=[
                {"role":"system","content":instance["text"].split("\n", 1)[0]},
                {"role":"user","content":instance["text"].split("\n", 1)[1]},
            ],
            temperature=0.7
        )
        content = response.choices[0].message.content.strip()
        instance["bug_report"] = content
        print(f"Generated bug report: {content}")
        res.append(instance)
    return res


def main(dataset_name_or_path: str,split:str, num_samples: int, output_dir: str):
    # 加载数据集
    openai_api = os.getenv("OPENAI_API_KEY")
    dataset_hf = create_text_dataset(dataset_name_or_path=dataset_name_or_path,splits=[split],validation_ratio=0,output_dir="",prompt_style="bug_report",file_source="oracle",retrieval_file=None, k=None,max_context_len=None,nname="rustbench_100",tokenizer_name=None,push_to_hub_user=None)
    dataset = [x for x in dataset_hf]
    code_entries = make_code_snippet(dataset_name_or_path, split=split ,output=None)
    bug_report_dataset = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(generate_bug_report,num_samples ,instance, openai_api) for instance in dataset]

        for future in tqdm(as_completed(futures), total=len(futures), desc="Processing"):
            try:
                result = future.result()
                bug_report_dataset.extend(result)
            except Exception as e:
                print(f"Error processing example: {e}")
    
    def add_code_snippet(example):
        for code in code_entries:
            if example["instance_id"] == code["instance_id"]:
                example["code_snippet"] = code["code_snippet"]
                break
        return example
    
    dataset = bug_report_dataset.map(add_code_snippet) #在bug report dataset的基础上添加code snippet
    res = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(run_inference, sample ,openai_api) for sample in dataset]

        for future in tqdm(as_completed(futures), total=len(futures), desc="Processing"):
            try:
                result = future.result()
                res.append(result)
            except Exception as e:
                print(f"Error processing example: {e}")

    output_file = os.path.join(output_dir, "res.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        for entry in code_entries:
            # 查找匹配的 response 数据
            matching_response = next((r for r in res if r["instance_id"] == entry["instance_id"]), None)
            if matching_response:
                merged_json = {
                    "code_snippet": entry["code_snippet"],
                    "target_function": entry["target_function"],
                    "review_type": entry["review_type"],
                    "issue_detail": {
                        "problem_type": matching_response["problem_type"],
                        "location": entry["issue_detail"]["location"],
                        "level": matching_response["level"],
                        "description": matching_response["bug_report"],
                        "level_reason": matching_response["level_reason"]
                    },
                    "repo": entry["repo"],
                    "branch": entry["branch"],
                    "file_path": entry["file_path"],
                    "language": entry["language"]
                }
                # 将每条记录写入 JSONL 文件
                f.write(json.dumps(merged_json, ensure_ascii=False) + '\n')


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset_name_or_path", type=str, default="r1v3r/RustGPT_Bench_100", help="Dataset name or path")
    parser.add_argument("--num_samples", type=int, default=2, help="Number of samples to generate")
    parser.add_argument("--split", type=str, default="train", help="Split to use")
    parser.add_argument("--output_dir", type=str, default="/home/riv3r/Rust-bench/swebench/utils/delivery/output", help="Output directory")
    main(**vars(parser.parse_args()))




    




    #添加相关文件
    # input_instances_copy = {x["instance_id"]: x for x in dataset}
    # with TemporaryDirectory(
    #     dir="/scratch" if os.path.exists("/scratch") else "/tmp"
    # ) as root_dir:
    #     for instance_id, instance in tqdm(
    #         input_instances_copy.items(),
    #         total=len(input_instances_copy),
    #         desc="Adding text inputs",
    #     ):
    #         try:
    #             with AutoContextManager(
    #                 instance, root_dir, verbose=verbose
    #             ) as cm:
    #                 readmes = cm.get_readme_files
                    
    #         except:

    #             pass

    # with ThreadPoolExecutor(max_workers=10) as executor:
    #     futures = [executor.submit(run_api, instance, openai_api) for instance in dataset]

    #     for future in tqdm(as_completed(futures), total=len(futures), desc="Processing"):
    #         try:
    #             result = future.result()
    #             entries.append(result)
    #         except Exception as e:
    #             print(f"Error processing example: {e}")

    # entries = []
    # # 使用 ThreadPoolExecutor 实现多线程
    # with ThreadPoolExecutor(max_workers=10) as executor:  # 调整 max_workers 以控制线程数
    #     futures = [executor.submit(process_example, example, openai_api) for example in dataset]

    #     # 等待所有任务完成并收集结果，同时显示进度条
    #     for future in tqdm(as_completed(futures), total=len(futures), desc="Processing"):
    #         try:
    #             result = future.result()
    #             entries.append(result)
    #         except Exception as e:
    #             print(f"Error processing example: {e}")

    # # 将结果保存到文件
    # with open("classification_results.json", "w", encoding="utf-8") as f:
    #     json.dump(entries, f, ensure_ascii=False, indent=4)