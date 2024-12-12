import os,json

def check_log():
    path_log = os.path.join(os.getcwd(), f"logs/pr_log")
    pr_done = []
    with open(path_log, "r") as f:
        lines = f.read().splitlines()
        for line in lines:
            if line.startswith("Done"):
                repo_name = line.split(':')[1].strip()
                pr_done.append(repo_name)
    return pr_done

# 
def check_num(repo_names):
    path_log = os.path.join(os.getcwd(), f"logs/pr_log")
    repo_max_numbers = {name: 0 for name in repo_names}

    with open(path_log, "r") as f:
        lines = f.read().splitlines()
        for line in lines:
            for repo_name in repo_names:
                if line.startswith(repo_name):
                    temp = line.split(':')[1].strip()
                    num = int(temp.split(' ')[0])
                    if num > repo_max_numbers[repo_name]:
                        repo_max_numbers[repo_name] = num

    return repo_max_numbers

def save_to_json(data, filename):
    with open(filename, 'w') as json_file:
        json.dump(data, json_file, indent=4)


def main():
    pr_done = check_log()
    result = check_num(pr_done)
    save_to_json(result, 'logs/pr_done.json')
    

if __name__ == '__main__':
    main()