import json
import os
from get_tasks_pipeline import main as get_tasks_pipeline

def load_json_to_list(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)  
    return data

def set_tokens():
    github_tokens = ""
    with open("tokens", "r") as file:
        a = file.read()
        tokens = a.split("\n")
        github_tokens = ','.join(tokens)
        os.environ['GITHUB_TOKENS'] = github_tokens

if __name__ == '__main__':
    file_path = 'rust_repos_diff_227.json'
    path_prs = '/home/riv3r/SWE-bench/swebench/collect/prs'
    path_tasks = '/home/riv3r/SWE-bench/swebench/collect/tasks'
    set_tokens()

    data_list = load_json_to_list(file_path)
    get_tasks_pipeline(repos=data_list,path_prs=path_prs,pull_numbers=None,path_tasks=path_tasks,mode="new",auto=True)

# repos: list,
#         path_prs: str,
#         path_tasks: str,
#         mode:str,
#         pull_numbers: list,
#         max_pulls: int = None,
#         cutoff_date: str = None,
#         auto: bool = False,

