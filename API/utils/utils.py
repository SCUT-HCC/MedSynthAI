import os
import json

# 创建文件夹
def create_folder(folder_path):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    return folder_path

def load_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)
    
def get_files_by_type(folder_path, file_type):
    """
    获取指定文件夹中特定类型的文件列表
    
    Args:
        folder_path (str): 要搜索的文件夹路径
        file_type (str): 文件类型（例如：'.txt', '.jpg'）
        
    Returns:
        list: 包含所有匹配文件路径的列表
    """
    files = []
    # 确保文件类型以点号开头
    if not file_type.startswith('.'):
        file_type = '.' + file_type
        
    # 检查文件夹是否存在
    if not os.path.exists(folder_path):
        return files
    
    # 遍历文件夹
    for file in os.listdir(folder_path):
        if file.endswith(file_type):
            # 获取完整文件路径
            full_path = os.path.join(folder_path, file)
            files.append(full_path)
            
    return files
    
