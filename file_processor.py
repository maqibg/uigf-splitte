#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UIGF/SRGF 抽卡记录分离工具 - 文件处理器模块
提供UIGF/SRGF格式文件的处理和转换功能

by: 马乞
GitHub: https://github.com/maqibg/yunzai-uigf-splitte
"""

import json
import os
from game_config import GameConfig
from utils import validate_json_structure, create_output_directory, format_progress_message


class FileProcessor:
    """文件处理器类，负责处理UIGF/SRGF格式文件的读取、验证和转换"""
    
    def __init__(self, game_type):
        """
        初始化文件处理器
        
        Args:
            game_type (str): 游戏类型 ("genshin" 或 "starrail")
        """
        self.game_type = game_type
        self.gacha_types = GameConfig.get_gacha_types(game_type)
        self.format_info = GameConfig.get_file_format_info(game_type)
        
        if not self.gacha_types:
            raise ValueError(f"不支持的游戏类型: {game_type}")
    
    def validate_file(self, file_path):
        """
        验证文件格式是否有效
        
        Args:
            file_path (str): 文件路径
            
        Returns:
            tuple: (is_valid, error_message)
                   is_valid (bool): 是否有效
                   error_message (str): 错误信息，如果有效则为None
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                return False, f"文件不存在: {file_path}"
            
            # 检查是否为文件（而不是目录）
            if not os.path.isfile(file_path):
                return False, f"指定路径不是文件: {file_path}"
            
            # 检查文件大小
            try:
                file_size = os.path.getsize(file_path)
                if file_size == 0:
                    return False, "文件为空，请选择有效的抽卡记录文件"
                if file_size > 100 * 1024 * 1024:  # 100MB限制
                    return False, "文件过大（超过100MB），请确认这是正确的抽卡记录文件"
            except OSError as e:
                return False, f"无法获取文件大小: {str(e)}"
            
            # 检查文件扩展名
            if not file_path.lower().endswith('.json'):
                return False, "文件扩展名不正确，请选择.json格式的文件"
            
            # 检查文件是否可读
            if not os.access(file_path, os.R_OK):
                return False, f"文件不可读，请检查文件权限: {file_path}"
            
            # 尝试加载JSON数据
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except json.JSONDecodeError as e:
                line_info = ""
                if hasattr(e, 'lineno') and hasattr(e, 'colno'):
                    line_info = f" (第{e.lineno}行，第{e.colno}列)"
                return False, f"JSON格式错误{line_info}: {e.msg}"
            except UnicodeDecodeError as e:
                return False, f"文件编码错误，请确保文件使用UTF-8编码: {str(e)}"
            except MemoryError:
                return False, "文件过大，内存不足，无法加载文件"
            except Exception as e:
                return False, f"读取文件时发生错误: {str(e)}"
            
            # 验证JSON结构
            is_valid, error_message = validate_json_structure(data, self.game_type)
            if not is_valid:
                return False, error_message
            
            # 额外验证：检查记录数量
            if "list" in data and isinstance(data["list"], list):
                record_count = len(data["list"])
                if record_count == 0:
                    return False, "文件中没有抽卡记录，请选择包含有效记录的文件"
                elif record_count > 50000:  # 合理的记录数量上限
                    return False, f"记录数量过多({record_count}条)，请确认这是正确的抽卡记录文件"
            
            return True, None
            
        except PermissionError:
            return False, f"权限不足，无法访问文件: {file_path}"
        except FileNotFoundError:
            return False, f"文件不存在: {file_path}"
        except Exception as e:
            return False, f"验证文件时发生未知错误: {str(e)}"
    
    def load_data(self, file_path):
        """
        加载JSON数据
        
        Args:
            file_path (str): 文件路径
            
        Returns:
            tuple: (data, error_message)
                   data (dict): 加载的数据，如果失败则为None
                   error_message (str): 错误信息，如果成功则为None
        """
        try:
            # 首先验证文件
            is_valid, error_message = self.validate_file(file_path)
            if not is_valid:
                return None, error_message
            
            # 加载数据
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return data, None
            
        except Exception as e:
            return None, f"加载文件时发生错误: {str(e)}"
    
    def process_records(self, data, output_dir, progress_callback=None):
        """
        处理记录并按gacha_type分离到不同文件
        
        Args:
            data (dict): 加载的UIGF/SRGF数据
            output_dir (str): 输出目录路径
            progress_callback (callable): 进度回调函数，接收(current, total, message)参数
            
        Returns:
            tuple: (success, error_message, stats)
                   success (bool): 是否成功
                   error_message (str): 错误信息，如果成功则为None
                   stats (dict): 处理统计信息
        """
        try:
            # 确保输出目录存在
            success, error_msg = create_output_directory(output_dir)
            if not success:
                return False, error_msg, None
            
            # 获取记录列表
            if "list" not in data or not isinstance(data["list"], list):
                return False, "数据中没有有效的记录列表", None
            
            records = data["list"]
            total_records = len(records)
            
            if total_records == 0:
                return True, None, {"total_records": 0, "processed_records": 0, "gacha_types": {}}
            
            # 从info中提取UID和其他信息
            uid = ""
            lang = "zh-cn"  # 默认语言
            if "info" in data and isinstance(data["info"], dict):
                info = data["info"]
                uid = str(info.get("uid", ""))
                lang = info.get("lang", "zh-cn")
            
            # 按gacha_type分组记录
            records_by_type = {}
            processed_count = 0
            skipped_count = 0
            
            for i, record in enumerate(records):
                try:
                    # 检查记录是否有效
                    if not isinstance(record, dict) or "gacha_type" not in record:
                        skipped_count += 1
                        continue
                    
                    original_gacha_type = str(record["gacha_type"])
                    
                    # 检查gacha_type是否在支持的列表中（合并前检查）
                    if original_gacha_type not in self.gacha_types:
                        skipped_count += 1
                        continue
                    
                    # 应用gacha_type合并逻辑
                    target_gacha_type = GameConfig.should_merge_gacha_type(self.game_type, original_gacha_type)
                    
                    # 如果需要合并，更新记录中的gacha_type字段
                    if target_gacha_type != original_gacha_type:
                        record = record.copy()  # 创建副本避免修改原始数据
                        record["gacha_type"] = target_gacha_type
                    
                    # 创建标准化的记录，确保字段顺序和完整性
                    processed_record = self._normalize_record(record, uid, lang)
                    
                    # 添加到对应的分组（使用target_gacha_type决定文件名）
                    if target_gacha_type not in records_by_type:
                        records_by_type[target_gacha_type] = []
                    
                    records_by_type[target_gacha_type].append(processed_record)
                    processed_count += 1
                    
                    # 调用进度回调
                    if progress_callback and (i + 1) % 100 == 0:  # 每100条记录更新一次进度
                        message = format_progress_message(i + 1, total_records, "所有类型")
                        progress_callback(i + 1, total_records, message)
                
                except Exception as e:
                    # 记录处理错误，跳过这条记录
                    skipped_count += 1
                    continue
            
            # 最终进度更新
            if progress_callback:
                progress_callback(total_records, total_records, "记录处理完成")
            
            # 保存分组后的记录
            save_success, save_error = self.save_records_by_type(records_by_type, output_dir)
            if not save_success:
                return False, save_error, None
            
            # 生成统计信息
            stats = {
                "total_records": total_records,
                "processed_records": processed_count,
                "skipped_records": skipped_count,
                "gacha_types": {}
            }
            
            for gacha_type, type_records in records_by_type.items():
                stats["gacha_types"][gacha_type] = len(type_records)
            
            return True, None, stats
            
        except Exception as e:
            return False, f"处理记录时发生错误: {str(e)}", None
    
    def save_records_by_type(self, records_dict, output_dir):
        """
        按类型保存记录到文件
        
        Args:
            records_dict (dict): 按gacha_type分组的记录字典
            output_dir (str): 输出目录路径
            
        Returns:
            tuple: (success, error_message)
                   success (bool): 是否成功
                   error_message (str): 错误信息，如果成功则为None
        """
        try:
            saved_files = []
            
            # 检查磁盘空间
            try:
                import shutil
                free_space = shutil.disk_usage(output_dir).free
                # 估算需要的空间（每条记录大约500字节）
                total_records = sum(len(records) for records in records_dict.values())
                estimated_size = total_records * 500  # 估算大小
                
                if free_space < estimated_size * 2:  # 保留2倍空间作为缓冲
                    return False, f"磁盘空间不足。需要约{estimated_size // (1024*1024)}MB，剩余{free_space // (1024*1024)}MB"
            except Exception:
                # 如果无法检查磁盘空间，继续执行
                pass
            
            for gacha_type, records in records_dict.items():
                if not records:  # 跳过空的记录列表
                    continue
                
                # 按id字段从大到小排序记录，如果没有id字段则按time字段排序
                def sort_records(records_list):
                    # 检查第一条记录来确定排序策略
                    if not records_list:
                        return records_list
                    
                    first_record = records_list[0]
                    
                    # 优先使用id字段排序
                    if 'id' in first_record and first_record['id']:
                        try:
                            return sorted(records_list, key=lambda x: int(x.get('id', '0')), reverse=True)
                        except (ValueError, TypeError):
                            # 如果id字段无法转换为整数，则按字符串排序
                            return sorted(records_list, key=lambda x: str(x.get('id', '')), reverse=True)
                    
                    # 如果没有id字段，使用time字段排序
                    elif 'time' in first_record and first_record['time']:
                        return sorted(records_list, key=lambda x: str(x.get('time', '')), reverse=True)
                    
                    # 如果既没有id也没有time字段，报错
                    else:
                        raise ValueError(f"记录缺少必要的排序字段（id或time）: {gacha_type}")
                
                try:
                    sorted_records = sort_records(records)
                except ValueError as e:
                    return False, str(e)
                
                # 构建输出文件路径
                filename = f"{gacha_type}.json"
                file_path = os.path.join(output_dir, filename)
                
                # 检查文件路径长度
                if len(file_path) > 260:
                    return False, f"文件路径过长（超过260字符）：{file_path}"
                
                try:
                    # 保存排序后的记录到JSON文件
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(sorted_records, f, ensure_ascii=False, indent=2, separators=(',', ': '))
                    
                    # 验证文件是否成功写入
                    if not os.path.exists(file_path):
                        return False, f"文件写入失败，文件不存在：{file_path}"
                    
                    # 检查文件大小是否合理
                    file_size = os.path.getsize(file_path)
                    if file_size == 0:
                        return False, f"文件写入失败，文件为空：{file_path}"
                    
                    saved_files.append(filename)
                    
                except PermissionError:
                    return False, f"权限不足，无法写入文件：{file_path}。请检查目录权限或以管理员身份运行程序"
                except OSError as e:
                    if e.errno == 28:  # No space left on device
                        return False, f"磁盘空间不足，无法写入文件：{file_path}"
                    elif e.errno == 13:  # Permission denied
                        return False, f"权限不足，无法写入文件：{file_path}"
                    elif e.errno == 36:  # File name too long
                        return False, f"文件名过长：{file_path}"
                    elif e.errno == 2:   # No such file or directory
                        return False, f"目录不存在：{output_dir}"
                    else:
                        return False, f"写入文件时发生系统错误（错误代码{e.errno}）：{file_path} - {str(e)}"
                except UnicodeEncodeError as e:
                    return False, f"文件编码错误，无法写入文件：{file_path} - {str(e)}"
                except MemoryError:
                    return False, f"内存不足，无法处理文件：{file_path}。请尝试处理较小的数据文件"
                except Exception as e:
                    return False, f"保存文件时发生未知错误：{file_path} - {str(e)}"
            
            if not saved_files:
                return False, "没有有效的记录需要保存"
            
            return True, None
            
        except Exception as e:
            return False, f"保存记录时发生未知错误: {str(e)}"
    
    def _normalize_record(self, record, uid, default_lang):
        """
        标准化记录格式，确保字段顺序和完整性
        
        Args:
            record (dict): 原始记录
            uid (str): 用户ID
            default_lang (str): 默认语言设置（从info中提取）
            
        Returns:
            dict: 标准化后的记录
        """
        # 按照示例格式创建记录，严格按照字段顺序
        normalized = {
            "uid": uid,
            "gacha_type": str(record.get("gacha_type", "")),
            "item_id": str(record.get("item_id", ""))
        }
        
        # count字段为非必要项，只有原始数据中存在时才添加
        if "count" in record:
            normalized["count"] = str(record["count"])
        
        # 继续添加其他必要字段
        normalized.update({
            "time": str(record.get("time", "")),
            "name": str(record.get("name", "")),
            "lang": str(record.get("lang", default_lang)),  # 优先使用记录中的lang，否则使用默认值
            "item_type": str(record.get("item_type", "")),
            "rank_type": str(record.get("rank_type", "")),
            "id": str(record.get("id", ""))
        })
        
        return normalized