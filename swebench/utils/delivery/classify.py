import os
import json
from datasets import load_dataset
import openai
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

def classify_with_openai(problem_statement, openai_api_key, model="gpt-4o-2024-08-06"):
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
    system_messages = "您是一个专业的问题分类助手。"

    # 构建修改后的 prompt
    prompt = (
        f"{system_messages}\n\n"
        f"问题陈述: \"{problem_statement}\"\n\n"
        f"请你将问题陈述总结为一段不超过300个字，辅以相关代码示例的描述，这里称之为描述(description)。\n"
        f"请将问题分类为一个类型，类型名称不超过十个汉字。您可以根据需要定义类型类别(problem_type)。\n"
        f"接下来，评估case级别(level)为“low”或“high”之一：\n"
        f"- 'low' 表示低价值问题，代表该问题并不需要甚至是一个误判的case，希望引导大模型在review类似的问题时能够降低其优先级，降低review的噪声\n"
        f"- 'high' 表示高价值问题，代表这类问题确实是用户所需要发现的，存在真正隐患的代码需要去解决。\n"
        f"最后，请详细解释您的评估理由(level_reason)。请提供一个详细的思考过程来支持您的分类，而不是一句话。\n"
        f"请将描述（description）限定在300字以内，并以中文描述为主，辅以相关代码示例。\n"
        f"请将严重程度的理由（level_reason）限定在300字以内，并以中文描述为主，辅以相关代码示例。\n"
        f"你返回的json键名中不能含有换行符"
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

def process_example(example, openai_api_key):
    """
    处理单个示例，调用 OpenAI API 进行分类。
    
    Args:
        example (dict): 数据集中的单个示例。
        openai_api_key (str): OpenAI API 密钥。
    
    Returns:
        dict: 包含分类结果的字典。
    """
    problem_statement = example["problem_statement"]
    response_json = classify_with_openai(problem_statement, openai_api_key)
    return {
        "instance_id": example["instance_id"],
        "description": response_json["description"],
        "problem_type": response_json["problem_type"],
        "severity_level": response_json["level"],
        "reason": response_json["level_reason"]
    }

def main():
    # 加载数据集
    dataset = load_dataset("r1v3r/auto_0207_bug", split="train")
    openai_api = os.getenv("OPENAI_API_KEY")

    entries = []
    # 使用 ThreadPoolExecutor 实现多线程
    with ThreadPoolExecutor(max_workers=10) as executor:  # 调整 max_workers 以控制线程数
        futures = [executor.submit(process_example, example, openai_api) for example in dataset]

        # 等待所有任务完成并收集结果，同时显示进度条
        for future in tqdm(as_completed(futures), total=len(futures), desc="Processing"):
            try:
                result = future.result()
                entries.append(result)
            except Exception as e:
                print(f"Error processing example: {e}")

    # 将结果保存到文件
    with open("classification_results.json", "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    main()