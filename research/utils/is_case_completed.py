"""
检查指定case是否已经完成工作流处理。
确保每个 case 的日志文件是完整的。
删除任何不完整或无效的日志文件。
返回该 case 是否已完成工作流处理。
"""
import os
import glob
import json
import logging
def is_case_completed(log_dir: str, case_index: int) -> bool:
    """
    检查指定case是否已经完成工作流
    如果存在不完整的文件则删除，确保每个case在目录中只出现一次
    
    Args:
        log_dir: 日志目录
        case_index: case序号
        
    Returns:
        bool: 如果case已完成返回True，否则返回False
    """
    # 构建文件路径模式：workflow_*_case_{case_index:04d}.jsonl
    pattern = os.path.join(log_dir, f"workflow_*_case_{case_index:04d}.jsonl")
    matching_files = glob.glob(pattern)
    
    if not matching_files:
        return False
    
    # 应该只有一个匹配的文件
    if len(matching_files) > 1:
        logging.warning(f"发现多个匹配文件 case {case_index}: {matching_files}")
    
    # 检查每个匹配的文件
    for log_file in matching_files:
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                # 读取最后一行
                lines = f.readlines()
                if not lines:
                    # 文件为空，删除
                    try:
                        os.remove(log_file)
                        logging.info(f"删除空文件: {log_file}")
                    except (OSError, FileNotFoundError, PermissionError) as e:
                        # 文件删除失败不影响主流程，记录警告即可
                        logging.warning(f"无法删除空文件 {log_file}: {e}")
                    continue
                
                last_line = lines[-1].strip()
                if not last_line:
                    # 最后一行为空，删除
                    try:
                        os.remove(log_file)
                        logging.info(f"删除最后一行为空的文件: {log_file}")
                    except (OSError, FileNotFoundError, PermissionError) as e:
                        # 文件删除失败不影响主流程，记录警告即可
                        logging.warning(f"无法删除最后一行为空的文件 {log_file}: {e}")
                    continue
                
                # 解析最后一行的JSON
                try:
                    last_entry = json.loads(last_line)
                    if last_entry.get("event_type") == "workflow_complete":
                        # 找到完整的文件
                        logging.info(f"发现已完成的case {case_index}: {log_file}")
                        return True
                    else:
                        # 文件不完整，删除
                        try:
                            os.remove(log_file)
                            logging.info(f"删除不完整的文件: {log_file}")
                        except (OSError, FileNotFoundError, PermissionError) as e:
                            # 文件删除失败不影响主流程，记录警告即可
                            logging.warning(f"无法删除不完整的文件 {log_file}: {e}")
                        continue
                        
                except json.JSONDecodeError:
                    # JSON解析失败，删除文件
                    try:
                        os.remove(log_file)
                        logging.info(f"删除JSON格式错误的文件: {log_file}")
                    except (OSError, FileNotFoundError, PermissionError) as e:
                        # 文件删除失败不影响主流程，记录警告即可
                        logging.warning(f"无法删除JSON格式错误的文件 {log_file}: {e}")
                    continue
                    
        except Exception as e:
            logging.warning(f"检查文件 {log_file} 时出错: {e}")
            # 出现异常也删除文件，避免后续问题
            try:
                os.remove(log_file)
                logging.info(f"删除异常文件: {log_file}")
            except (OSError, FileNotFoundError, PermissionError) as delete_error:
                # 修复1：明确指定要捕获的异常类型
                # 修复2：添加解释性注释
                # 文件删除失败不是致命错误，可能是权限问题或文件已被其他进程占用
                # 记录警告后继续处理，不中断整个检查流程
                logging.warning(f"无法删除异常文件 {log_file}: {delete_error}")
            except Exception as unexpected_error:
                # 处理其他意外的删除异常（比如磁盘满等）
                # 这些错误也不应该中断检查流程
                logging.error(f"删除文件时发生意外错误 {log_file}: {unexpected_error}")
            continue
    
    # 所有匹配的文件都被删除或没有完整的文件
    return False