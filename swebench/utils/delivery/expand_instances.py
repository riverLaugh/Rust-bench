import argparse
import os
import json
from datasets import load_dataset,Dataset
from numpy import var
import openai
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from swebench.inference.make_datasets.create_text_dataset import main as create_text_dataset
from swebench.utils.delivery.transfer_dataset import main as make_code_snippet
from swebench.inference.make_datasets.utils import AutoContextManager
from tempfile import TemporaryDirectory
from swebench.inference.make_datasets.utils import AutoContextManager, ingest_directory_contents

def check(problem_statement,code_snippet,num_reports, openai_api_key, model="gpt-4o-2024-08-06") ->dict:
    """
    使用 OpenAI API 获取问题类型和等级判定原因。
    
    Args:
        problem_statement (str): 问题陈述。
        openai_api_key (str): OpenAI API 密钥。
        model (str): 使用的模型名称。
    
    Returns:
        tuple: (problem_type, severity_level, reason)
    """
    openai.api_key = openai_api_key
    openai.base_url = "https://api5.xhub.chat/v1/"
    system_messages = "您是一个专业的问题分类助手，专门分析代码中的潜在问题，并提供详细的分类和评估。"

    prompt = (
        f"{system_messages}\n\n"
        f"以下是用户提供的问题陈述和相关的代码片段，请结合两者进行分析。\n\n"
        f"问题陈述: \"{problem_statement}\"\n\n"
        f"代码片段: \"{code_snippet}\"\n\n"
        f"请生成一个不超过 300 字的描述（description），总结问题的核心、代码中的具体表现以及可能的影响，并辅以相关代码示例。\n"
        f"请将问题分类为一个类型（problem_type），类型名称不超过十个汉字。常见问题类型包括：逻辑错误、性能问题、安全漏洞、代码风格问题等。您可根据情况选择或定义新类型。\n"
        f"接下来，评估 case 级别（level）为 'low' 或 'high' 之一：\n"
        f"- 'low' 表示低价值问题，例如误报的 lint 警告，希望引导大模型在 review 类似问题时降低优先级。\n"
        f"- 'high' 表示高价值问题，例如可能导致程序崩溃的错误，需要用户关注和解决。\n"
        f"最后，请提供一个详细的评估理由（level_reason），不超过 300 字，包括对代码的分析、问题的潜在影响以及您选择该级别的依据，辅以相关代码示例。\n"
        f"请确保所有回答使用中文，并严格遵守字数限制。\n"
        f"请以以下 JSON 格式返回您的回答，确保 JSON 键名是单行字符串，不包含换行符：\n"
        f"{{\n  \"description\": \"...\",\n  \"problem_type\": \"...\",\n  \"level\": \"...\",\n  \"level_reason\": \"...\"\n}}"
    )

    # 调用 OpenAI API
    try:
        for i in range(num_reports):
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
                                "description": {"type": "string"},
                                "problem_type": {"type": "string"},
                                "level": {"type": "string"},
                                "level_reason": {"type": "string"}
                            },
                            "required": ["description", "problem_type", "level", "level_reason"]
                        }
                    }
                }
            )
            content = response.choices[0].message.content.strip()
            response_json = json.loads(content)
        return response_json
    except Exception as e:
        print(f"OpenAI API error: {e}")
        return {
            "description": "Unknown",
            "problem_type": "Unknown",
            "level": "Unknown",
            "level_reason": "Unknown"
        }



def generate_bug_report(instance, openai_api,model) -> dict:
    """
    处理单个示例，调用 OpenAI API 进行分类。
    
    Args:
        instance (dict): 数据集中的单个示例。
        openai_api (str): OpenAI API 密钥。
    
    Returns:
        dict: 包含分类结果的字典。
    """
    openai.api_key = openai_api
    openai.base_url = "https://api5.xhub.chat/v1/"
    response = openai.chat.completions.create(
        model=model,
        messages=[
            {"role":"system","content":instance["text"].split("\n", 1)[0]},
            {"role":"user","content":instance["text"].split("\n", 1)[1]},
        ],
        temperature=0.3
    )
    content = response.choices[0].message.content.strip()
    return{"instance_id":instance["instance_id"],"bug_report":content}


def merge_json(entry_data, response_data, output_file):
    """
    读取两个 JSON 文件，根据 instance_id 合并，并保存为 JSONL 文件。

    :param entry_file: 包含代码片段等信息的 JSON 文件路径。
    :param response_file: 包含问题类型等信息的 JSON 文件路径。
    :param output_file: 输出 JSONL 文件路径。
    """
    # 构建合并后的数据
    with open(output_file, 'w', encoding='utf-8') as f:
        for entry in entry_data:
            # 查找匹配的 response 数据
            matching_response = next((r for r in response_data if r["instance_id"] == entry["instance_id"]), None)
            if matching_response:
                merged_json = {
                    "code_snippet": entry["code_snippet"],
                    "target_function": entry["target_function"],
                    "review_type": entry["review_type"],
                    "issue_detail": {
                        "problem_type": matching_response["problem_type"],
                        "location": entry["issue_detail"]["location"],
                        "level": matching_response["severity_level"],
                        "description": matching_response["description"],
                        "level_reason": matching_response["reason"]
                    },
                    "repo": entry["repo"],
                    "branch": entry["branch"],
                    "file_path": entry["file_path"],
                    "language": entry["language"]
                }
                # 将每条记录写入 JSONL 文件
                f.write(json.dumps(merged_json, ensure_ascii=False) + '\n')
    print(f"Merged JSONL saved to {output_file}")




def main(dataset_name_or_path: str, num_samples: int, output_dir: str):
    # 加载数据集
    openai_api = os.getenv("OPENAI_API_KEY")
    dataset = create_text_dataset(dataset_name_or_path="r1v3r/RustGPT_Bench_100",splits="train",validation_ratio=0,output_dir="",prompt_style="bug_report",file_source="oracle")
    code_entries = make_code_snippet("r1v3r/RustGPT_Bench_100", openai_api,output=None)
    bug_report = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(generate_bug_report, instance, openai_api) for instance in dataset]

        for future in tqdm(as_completed(futures), total=len(futures), desc="Processing"):
            try:
                result = future.result()
                bug_report.append(result)
            except Exception as e:
                print(f"Error processing example: {e}")

    with open("bug_report.json", "w", encoding="utf-8") as f:
        json.dump(bug_report, f, indent=4)
        
    def add_code_snippet(example):
        for code in code_entries:
            if example["instance_id"] == code["instance_id"]:
                example["code_snippet"] = code["code_snippet"]
                break
        return example
    dataset = dataset.map(add_code_snippet)
    check_res = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(check, sample["text"], sample["code_snippet"], openai_api,num_samples) for sample in dataset]

        for future in tqdm(as_completed(futures), total=len(futures), desc="Processing"):
            try:
                result = future.result()
                check_res.append(result)
            except Exception as e:
                print(f"Error processing example: {e}")

    merge_json(code_entries,check_res,"final.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset_name_or_path", type=str, default="r1v3r/RustGPT_Bench_100", help="Dataset name or path")
    parser.add_argument("--num_samples", type=int, default=100, help="Number of samples to generate")
    parser.add_argument("--output_dir", type=str, default="", help="Output directory")
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

if __name__ == "__main__":
    main()