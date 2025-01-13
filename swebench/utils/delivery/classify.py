import argparse
import os
import sys
import json
import re
from datasets import load_dataset
from pathlib import Path
from tqdm import tqdm
import pandas as pd
import subprocess
import openai
import requests
import base64


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
    # system_messages = "You are an AI assistant that categorizes issues into predefined types and determines the severity level along with the reason."
    # 假设 system_messages 已定义
    system_messages = "您是一个专业的问题分类助手。"

    # 构建修改后的 prompt
    prompt = (
        f"{system_messages}\n\n"
        f"问题陈述: \"{problem_statement}\"\n\n"
        f"请你将问题陈述总结为一段不超过300个字，辅以相关代码示例的描述，这里称之为描述(description)。\n"
        f"请将问题分类为一个类型，类型名称不超过十个汉字。您可以根据需要定义类型类别(problem_type)。\n"
        f"接下来，评估严重程度等级(level)为“low”或“high”之一：\n"
        f"- 'low' 表示问题较小，不是 bug，但在某些情况下可能存在风险。\n"
        f"- 'high' 表示这是一个已确认的 bug。\n"
        f"最后，请详细解释您的理由(level_reason)。请提供一个详细的思考过程来支持您的分类，而不是一句话。\n"
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
        # json_cleaned = re.sub(r'"\n(.*?)":', r'"\1":', content)
        print(content)
        # 假设返回格式为：
        # Problem Type: Type1
        # Severity Level: low
        # Reason: ...
        response_json = json.loads(content)
        return response_json
    
    except Exception as e:
        print(f"OpenAI API error: {e}")
        # return "Unknown", "Unknown", "Unknown"



dataset = load_dataset("r1v3r/RustGPT_Bench_100",split="train")

openai_api = os.getenv("OPENAI_API_KEY")

entries = []

for example in dataset:
    problem_statement = example["problem_statement"]
    response_json = classify_with_openai(problem_statement, openai_api)
    entries.append({
        "instance_id": example["instance_id"],
        "description": response_json["description"],
        "problem_type": response_json["problem_type"],
        "severity_level": response_json["level"],
        "reason": response_json["level_reason"]
    })

with open("classification_results.json", "w") as f:
    json.dump(entries, f, indent=4)