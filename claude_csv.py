import json
import pandas as pd
import requests
import re
import os
from typing import Optional

# Load GitHub token from environment variable
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
if not GITHUB_TOKEN:
    print("Warning: GITHUB_TOKEN environment variable not set. API requests may be rate-limited.")
    GITHUB_TOKEN = None

def generate_pr_url(input_string: str) -> str:
    """
    Convert a string like 'owner__repo-pr_number' to a GitHub PR URL.
    
    Args:
        input_string: Input in the format 'owner__repo-pr_number'
        
    Returns:
        GitHub PR URL or error message if format is invalid
    """
    try:
        owner, repo_pr = input_string.split('__')
        repo, pr_number = repo_pr.split('-')
        return f"https://github.com/{owner}/{repo}/pull/{pr_number}"
    except ValueError:
        return "Error: Invalid input format. Expected 'owner__repo-pr_number'"

def get_trajs_file_url(instance: str, base_path: str, model: str) -> Optional[str]:
    """
    Use GitHub API to find a file matching 'Claude-{model}-*.json' in the trajs directory.
    
    Args:
        instance: Instance name (e.g., 'sharkdp__fd-555')
        base_path: Base GitHub API path for the trajs directory
        model: Model name (e.g., '3.5-Sonnet(Oct)' or '3.7-Sonnet')
        
    Returns:
        Full URL to the matching file or None if not found
    """
    repo = "multi-swe-bench/experiments"
    api_url = f"https://api.github.com/repos/{repo}/contents/{base_path}/trajs/{instance}"
    
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    try:
        print(f"Requesting API: {api_url}")
        response = requests.get(api_url, headers=headers)
        print(f"Status code: {response.status_code}")
        
        response.raise_for_status()
        files = response.json()
        
        # Debug: Print all files in the directory
        file_names = [f.get('name', '') for f in files if isinstance(f, dict)]
        print(f"Files found for {instance}: {file_names}")
        
        # Escape special characters in model name for regex
        escaped_model = re.escape(model)
        pattern = re.compile(rf"Claude-{escaped_model}-\d+\.\d+\.json")
        for file in files:
            if isinstance(file, dict) and pattern.match(file.get('name', '')):
                print(f"Matched file: {file.get('name')}")
                return file.get('download_url')
        print(f"No matching file found for pattern: Claude-{model}-*.json")
        return None
    except requests.RequestException as e:
        print(f"Error fetching files for {instance}: {e}")
        return None

# Load JSON data
try:
    cla_3_5 = json.load(open('/home/riv3r/SWE-bench/claude-3_5.json'))
    cla_3_7 = json.load(open('/home/riv3r/SWE-bench/claude-3_7.json'))
except FileNotFoundError as e:
    print(f"Error: File not found - {e}")
    exit(1)

resolve_3_5 = cla_3_5.get('resolved', [])
resolve_3_7 = cla_3_7.get('resolved', [])

# Get union of instances
all_instances = set(resolve_3_5).union(set(resolve_3_7))

# Base paths for trajs directories
base_path_3_5 = "evaluation/rust/verified/20250329_MopenHands_Claude-3.5-Sonnet(Oct)"
base_path_3_7 = "evaluation/rust/verified/20250329_MopenHands_Claude-3.7-Sonnet"

# Prepare data for CSV
data = []
for instance in all_instances:
    pr_url = generate_pr_url(instance)
    
    # Get trajs URLs using GitHub API
    trajs_3_5 = get_trajs_file_url(instance, base_path_3_5, "3.5-Sonnet(Oct)") if instance in resolve_3_5 else ""
    trajs_3_7 = get_trajs_file_url(instance, base_path_3_7, "3.7-Sonnet") if instance in resolve_3_7 else ""
    
    data.append({
        "instance": instance,
        "pr_url": pr_url,
        "trajs_3_5": trajs_3_5,
        "trajs_3_7": trajs_3_7
    })

# Create DataFrame and save to CSV
df = pd.DataFrame(data)
df.to_csv("instance_pr_trajs.csv", index=False)

# Print resolved instances for verification
print('3.5:', resolve_3_5)
print('3.7:', resolve_3_7)
print("CSV file 'instance_pr_trajs.csv' has been generated.")