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
    file_path = 'test.json'
    path_prs = '/Users/yjzhou/myworkspace/forked_repo/SWE-bench/swebench/collect/prs/auto'
    path_tasks = '/Users/yjzhou/myworkspace/forked_repo/SWE-bench/swebench/collect/tasks/auto'
    set_tokens()

    data_list = load_json_to_list(file_path)
    get_tasks_pipeline(data_list,path_prs,path_tasks,None,None,None,True)


