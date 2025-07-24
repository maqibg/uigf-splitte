#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UIGF/SRGF 抽卡记录分离工具 - 工具函数模块
提供通用的工具函数和验证逻辑

by: 马乞
GitHub: https://github.com/maqibg/yunzai-uigf-splitte
"""

import os
import json
from game_config import GameConfig


def validate_json_structure(data, game_type):
    """
    验证JSON结构是否符合UIGF/SRGF格式
    
    Args:
        data (dict): 解析后的JSON数据
        game_type (str): 游戏类型 ("genshin" 或 "starrail")
        
    Returns:
        tuple: (is_valid, error_message)
               is_valid (bool): 是否有效
               error_message (str): 错误信息，如果有效则为None
    """
    try:
        # 检查基本结构
        if not isinstance(data, dict):
            return False, "文件格式错误：根对象必须是JSON对象"
        
        # 检查必需的顶级字段
        if "info" not in data:
            return False, "文件格式错误：缺少info字段"
        
        if "list" not in data:
            return False, "文件格式错误：缺少list字段"
        
        # 检查info字段结构
        info = data["info"]
        if not isinstance(info, dict):
            return False, "文件格式错误：info字段必须是对象"
        
        # 检查info中的必需字段
        required_info_fields = ["uid", "lang", "export_time"]
        for field in required_info_fields:
            if field not in info:
                return False, f"文件格式错误：info中缺少{field}字段"
            # 检查字段值是否为空
            if not info[field] or str(info[field]).strip() == "":
                return False, f"文件格式错误：info中{field}字段不能为空"
        
        # 检查游戏特定的版本字段
        format_info = GameConfig.get_file_format_info(game_type)
        if format_info:
            version_field = format_info["version_field"]
            if version_field not in info:
                return False, f"文件格式错误：info中缺少{version_field}字段"
            if not info[version_field] or str(info[version_field]).strip() == "":
                return False, f"文件格式错误：info中{version_field}字段不能为空"
        
        # 检查list字段
        record_list = data["list"]
        if not isinstance(record_list, list):
            return False, "文件格式错误：list字段必须是数组"
        
        # 检查list中记录的结构（如果有记录的话）
        if len(record_list) > 0:
            # 检查前几条记录以确保数据一致性
            sample_size = min(5, len(record_list))
            
            for i in range(sample_size):
                record = record_list[i]
                
                if not isinstance(record, dict):
                    return False, f"文件格式错误：第{i+1}条记录必须是对象"
                
                # 检查记录的核心必需字段
                required_record_fields = [
                    "gacha_type", "time", "name", "item_type", 
                    "rank_type", "id"
                ]
                
                for field in required_record_fields:
                    if field not in record:
                        return False, f"文件格式错误：第{i+1}条记录中缺少{field}字段"
                    # 检查关键字段不能为空
                    if field in ["gacha_type", "time", "id"] and (not record[field] or str(record[field]).strip() == ""):
                        return False, f"文件格式错误：第{i+1}条记录中{field}字段不能为空"
                
                # 验证gacha_type是否为支持的类型
                gacha_type = str(record["gacha_type"])
                supported_types = GameConfig.get_gacha_types(game_type)
                if supported_types and gacha_type not in supported_types:
                    return False, f"文件格式错误：第{i+1}条记录中gacha_type '{gacha_type}' 不是{game_type}游戏支持的类型"
                
                # 验证时间格式（基本检查）
                time_str = str(record["time"])
                if len(time_str) < 10:  # 至少应该有日期部分
                    return False, f"文件格式错误：第{i+1}条记录中time字段格式不正确"
        
        return True, None
        
    except Exception as e:
        return False, f"验证过程中发生错误：{str(e)}"


def create_output_directory(path):
    """
    创建输出目录，如果目录不存在则创建
    
    Args:
        path (str): 目录路径
        
    Returns:
        tuple: (success, error_message)
               success (bool): 是否成功
               error_message (str): 错误信息，如果成功则为None
    """
    try:
        # 检查路径是否为空或无效
        if not path or not path.strip():
            return False, "目录路径不能为空"
        
        # 规范化路径
        path = os.path.abspath(path.strip())
        
        # 检查路径长度（Windows路径长度限制）
        if len(path) > 260:
            return False, f"目录路径过长（超过260字符）：{path}"
        
        # 检查路径是否已存在
        if os.path.exists(path):
            # 检查是否为目录
            if not os.path.isdir(path):
                return False, f"路径已存在但不是目录：{path}"
            
            # 检查是否可写
            if not os.access(path, os.W_OK):
                return False, f"目录不可写，请检查权限或选择其他目录：{path}"
            
            # 检查磁盘空间（至少需要100MB空间）
            try:
                import shutil
                free_space = shutil.disk_usage(path).free
                if free_space < 100 * 1024 * 1024:  # 100MB
                    return False, f"磁盘空间不足（剩余{free_space // (1024*1024)}MB），请清理磁盘空间或选择其他目录"
            except Exception:
                # 如果无法获取磁盘空间信息，继续执行
                pass
            
            return True, None
        
        # 检查父目录是否存在且可写
        parent_dir = os.path.dirname(path)
        if parent_dir and not os.path.exists(parent_dir):
            # 尝试创建父目录
            try:
                os.makedirs(parent_dir, exist_ok=True)
            except PermissionError:
                return False, f"权限不足，无法创建父目录：{parent_dir}"
            except OSError as e:
                if e.errno == 28:  # No space left on device
                    return False, f"磁盘空间不足，无法创建目录：{parent_dir}"
                elif e.errno == 13:  # Permission denied
                    return False, f"权限不足，无法创建目录：{parent_dir}"
                else:
                    return False, f"创建父目录时发生系统错误：{str(e)}"
        
        if parent_dir and not os.access(parent_dir, os.W_OK):
            return False, f"父目录不可写，请检查权限：{parent_dir}"
        
        # 创建目录（包括父目录）
        os.makedirs(path, exist_ok=True)
        
        # 验证创建成功并可写
        if not os.path.exists(path):
            return False, f"创建目录失败：{path}"
        
        if not os.access(path, os.W_OK):
            return False, f"创建的目录不可写，请检查权限：{path}"
        
        # 测试写入权限
        test_file = os.path.join(path, ".write_test")
        try:
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
        except PermissionError:
            return False, f"目录写入权限测试失败：{path}"
        except OSError as e:
            if e.errno == 28:  # No space left on device
                return False, f"磁盘空间不足：{path}"
            else:
                return False, f"目录写入测试失败：{str(e)}"
        
        return True, None
        
    except PermissionError:
        return False, f"权限不足，无法访问或创建目录：{path}。请以管理员身份运行程序或选择其他目录"
    except OSError as e:
        if e.errno == 28:  # No space left on device
            return False, f"磁盘空间不足，无法创建目录：{path}"
        elif e.errno == 13:  # Permission denied
            return False, f"权限不足，无法创建目录：{path}。请检查目录权限或以管理员身份运行"
        elif e.errno == 36:  # File name too long
            return False, f"目录路径过长：{path}"
        elif e.errno == 2:   # No such file or directory
            return False, f"父目录不存在且无法创建：{path}"
        else:
            return False, f"创建目录时发生系统错误（错误代码{e.errno}）：{str(e)}"
    except Exception as e:
        return False, f"创建目录时发生未知错误：{str(e)}"


def format_progress_message(current, total, gacha_type):
    """
    格式化进度消息
    
    Args:
        current (int): 当前处理的数量
        total (int): 总数量
        gacha_type (str): 当前处理的抽卡类型
        
    Returns:
        str: 格式化的进度消息
    """
    if total == 0:
        percentage = 0
    else:
        percentage = int((current / total) * 100)
    
    if gacha_type == "所有类型":
        return f"正在处理记录... ({current}/{total}, {percentage}%)"
    else:
        return f"正在处理抽卡类型 {gacha_type}... ({current}/{total}, {percentage}%)"


def extract_uid_from_data(data):
    """
    从UIGF/SRGF数据中提取UID
    
    Args:
        data (dict): 解析后的JSON数据
        
    Returns:
        str: UID字符串，如果提取失败则返回None
    """
    try:
        # 首先尝试从info字段中获取UID
        if "info" in data and isinstance(data["info"], dict):
            info = data["info"]
            if "uid" in info and info["uid"]:
                return str(info["uid"])
        
        # 如果info中没有UID，尝试从第一条记录中获取
        if "list" in data and isinstance(data["list"], list) and len(data["list"]) > 0:
            first_record = data["list"][0]
            if isinstance(first_record, dict) and "uid" in first_record and first_record["uid"]:
                return str(first_record["uid"])
        
        return None
        
    except Exception:
        return None