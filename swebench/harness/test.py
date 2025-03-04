import os

def delete_json_files_in_current_folder():
    # 获取当前文件夹路径
    current_folder = os.getcwd()
    
    # 遍历当前文件夹中的所有文件
    for file_name in os.listdir(current_folder):
        # 构造完整路径
        file_path = os.path.join(current_folder, file_name)
        
        # 检查文件是否是 .json 文件且是否是普通文件（排除子文件夹）
        if os.path.isfile(file_path) and file_name.endswith('.json'):
            try:
                # 删除文件
                os.remove(file_path)
                print(f"Deleted: {file_name}")
            except Exception as e:
                print(f"Failed to delete {file_name}: {e}")

if __name__ == '__main__':
    delete_json_files_in_current_folder()
