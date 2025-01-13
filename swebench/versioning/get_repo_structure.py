from github import Github
import requests
import base64
import toml

# 替换为您的 GitHub 访问令牌
ACCESS_TOKEN = 'your_github_token'

# 初始化 GitHub 客户端
g = Github(ACCESS_TOKEN)

# 获取仓库中的所有 Cargo.toml 文件
def get_cargo_toml_files(repo):
    cargo_toml_files = []
    contents = []
    try:
        contents.extend(repo.get_contents(""))
    except:
        return cargo_toml_files

    while contents:
        file_content = contents.pop(0)
        if file_content.type == 'dir':
            try:
                contents.extend(repo.get_contents(file_content.path))
            except:
                continue
        elif file_content.type == 'file' and file_content.name == 'Cargo.toml':
            cargo_toml_files.append(file_content)
    return cargo_toml_files

# 解析 Cargo.toml 文件，查找子项目
def find_subprojects_in_cargo_toml(file_content):
    # 获取文件内容
    content = base64.b64decode(file_content.content).decode('utf-8')
    try:
        cargo_data = toml.loads(content)
    except toml.TomlDecodeError:
        return []

    subprojects = []

    # 检查 [workspace] 部分
    if 'workspace' in cargo_data and 'members' in cargo_data['workspace']:
        members = cargo_data['workspace']['members']
        subprojects.extend(members)

    return subprojects