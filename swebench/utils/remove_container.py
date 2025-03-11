import docker

# 初始化 Docker 客户端
client = docker.from_env()

# 获取所有容器
containers = client.containers.list(all=True)

# 遍历容器
for container in containers:
    # 获取容器的名称（去掉前面的斜杠）
    container_name = container.name

    # 检查名称是否以 "/sweb.eval" 开头
    if container_name.startswith("sweb.eval"):
        print(f"Deleting container: {container_name} (ID: {container.id})")
        try:
            # 强制删除容器
            container.remove(force=True)
            print(f"Successfully deleted container: {container_name}")
        except Exception as e:
            print(f"Failed to delete container {container_name}: {e}")