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
    system_messages = "You are an AI assistant that categorizes issues into predefined types and determines the severity level along with the reason."
    prompt = (
        f"{system_messages}\n\n"
        f"Problem Statement: \"{problem_statement}\"\n\n"
        f"Please classify the problem into a type with a name no longer than six words. You may define the type categories as needed.\n"
        f"Next, evaluate the severity level as either 'low' or 'high':\n"
        f"- 'Low' means the issue is minor, not a bug, but it could present risks in certain scenarios.\n"
        f"- 'High' means the issue is a confirmed bug.\n"
        f"Finally, explain your reasoning in detail. Provide a chain of thought to support your classification, rather than a single sentence.\n"
    )
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
                    "name":"response",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "problem_type": {"type": "string"},
                            "severity_level": {"type": "string"},
                            "reason": {"type": "string"}
                    }
                }
            }
        }
        )
        content = response.choices[0].message.content.strip()
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
        "problem_type": response_json["problem_type"],
        "severity_level": response_json["severity_level"],
        "reason": response_json["reason"]
    })

with open("classification_results.json", "w") as f:
    json.dump(entries, f, indent=4)