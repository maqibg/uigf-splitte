#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UIGF/SRGF 抽卡记录分离工具 - 文件修复模块
提供UIGF/SRGF格式文件的问题检测和修复功能

by: 马乞
GitHub: https://github.com/maqibg/yunzai-uigf-splitte
"""

import json
import os
import re
from datetime import datetime
from game_config import GameConfig
from utils import validate_json_structure, create_output_directory, extract_uid_from_data, validate_record_fields, sanitize_filename, format_progress_message


class FileRepairer:
    """文件修复器类，负责检测和修复UIGF/SRGF格式文件中的问题"""
    
    def __init__(self, game_type):
        """
        初始化文件修复器
        
        Args:
            game_type (str): 游戏类型 ("genshin" 或 "starrail")
        """
        self.game_type = game_type
        self.gacha_types = GameConfig.get_gacha_types(game_type)
        self.format_info = GameConfig.get_file_format_info(game_type)
        
        if not self.gacha_types:
            raise ValueError(f"不支持的游戏类型: {game_type}")
        
        # 定义必需字段
        self.required_info_fields = ["uid", "lang", "export_time"]
        self.required_record_fields = ["gacha_type", "time", "name", "item_type", "rank_type", "id"]
        
        # 添加游戏特定的版本字段
        if self.format_info:
            self.required_info_fields.append(self.format_info["version_field"])
    
    def analyze_file_issues(self, file_path):
        """
        分析文件中的格式问题
        
        Args:
            file_path (str): 文件路径
            
        Returns:
            tuple: (issues, data)
                   issues (dict): 发现的问题列表
                   data (dict): 加载的数据，如果加载失败则为None
        """
        issues = {
            "file_errors": [],
            "structure_errors": [],
            "info_errors": [],
            "record_errors": [],
            "duplicate_ids": [],
            "time_format_errors": [],
            "data_type_errors": []
        }
        
        try:
            # 检查文件是否存在和可读
            if not os.path.exists(file_path):
                issues["file_errors"].append(f"文件不存在: {file_path}")
                return issues, None
            
            if not os.path.isfile(file_path):
                issues["file_errors"].append(f"指定路径不是文件: {file_path}")
                return issues, None
            
            if not os.access(file_path, os.R_OK):
                issues["file_errors"].append(f"文件不可读: {file_path}")
                return issues, None
            
            # 尝试加载JSON数据
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except json.JSONDecodeError as e:
                issues["file_errors"].append(f"JSON格式错误: {e.msg}")
                return issues, None
            except UnicodeDecodeError as e:
                issues["file_errors"].append(f"文件编码错误: {str(e)}")
                return issues, None
            except Exception as e:
                issues["file_errors"].append(f"读取文件错误: {str(e)}")
                return issues, None
            
            # 检查基本结构
            if not isinstance(data, dict):
                issues["structure_errors"].append("根对象必须是JSON对象")
                return issues, data
            
            if "info" not in data:
                issues["structure_errors"].append("缺少info字段")
            elif not isinstance(data["info"], dict):
                issues["structure_errors"].append("info字段必须是对象")
            
            if "list" not in data:
                issues["structure_errors"].append("缺少list字段")
            elif not isinstance(data["list"], list):
                issues["structure_errors"].append("list字段必须是数组")
            
            # 如果基本结构有问题，返回
            if issues["structure_errors"]:
                return issues, data
            
            # 检查info字段问题
            self._analyze_info_issues(data["info"], issues)
            
            # 检查记录问题
            self._analyze_record_issues(data["list"], issues)
            
            return issues, data
            
        except Exception as e:
            issues["file_errors"].append(f"分析文件时发生错误: {str(e)}")
            return issues, None 
   
    def _analyze_info_issues(self, info, issues):
        """
        分析info字段中的问题
        
        Args:
            info (dict): info字段数据
            issues (dict): 问题列表字典
        """
        # 检查必需字段
        for field in self.required_info_fields:
            if field not in info:
                issues["info_errors"].append(f"info中缺少{field}字段")
            elif not info[field] or str(info[field]).strip() == "":
                issues["info_errors"].append(f"info中{field}字段为空")
            elif not isinstance(info[field], str):
                issues["data_type_errors"].append(f"info中{field}字段应为字符串类型")
    
    def _analyze_record_issues(self, records, issues):
        """
        分析记录列表中的问题
        
        Args:
            records (list): 记录列表
            issues (dict): 问题列表字典
        """
        if not records:
            return
        
        seen_ids = set()
        
        for i, record in enumerate(records):
            record_index = i + 1
            
            # 检查记录是否为对象
            if not isinstance(record, dict):
                issues["record_errors"].append(f"第{record_index}条记录必须是对象")
                continue
            
            # 检查必需字段
            for field in self.required_record_fields:
                if field not in record:
                    issues["record_errors"].append(f"第{record_index}条记录缺少{field}字段")
                elif field in ["gacha_type", "time", "id"] and (not record[field] or str(record[field]).strip() == ""):
                    issues["record_errors"].append(f"第{record_index}条记录{field}字段为空")
            
            # 检查数据类型
            self._check_record_data_types(record, record_index, issues)
            
            # 检查gacha_type是否有效
            if "gacha_type" in record and record["gacha_type"]:
                gacha_type = str(record["gacha_type"])
                if gacha_type not in self.gacha_types:
                    issues["record_errors"].append(f"第{record_index}条记录gacha_type '{gacha_type}' 不是有效类型")
            
            # 检查时间格式
            if "time" in record and record["time"]:
                time_str = str(record["time"])
                if not self._is_valid_time_format(time_str):
                    issues["time_format_errors"].append(f"第{record_index}条记录时间格式错误: {time_str}")
            
            # 检查重复ID
            if "id" in record and record["id"]:
                record_id = str(record["id"])
                if record_id in seen_ids:
                    issues["duplicate_ids"].append(f"第{record_index}条记录ID重复: {record_id}")
                else:
                    seen_ids.add(record_id)
    
    def _check_record_data_types(self, record, record_index, issues):
        """
        检查记录中字段的数据类型
        
        Args:
            record (dict): 记录对象
            record_index (int): 记录索引
            issues (dict): 问题列表字典
        """
        # 应该是字符串的字段
        string_fields = ["gacha_type", "time", "name", "item_type", "rank_type", "id", "uid", "lang", "item_id", "count"]
        
        for field in string_fields:
            if field in record and record[field] is not None:
                if not isinstance(record[field], str):
                    issues["data_type_errors"].append(f"第{record_index}条记录{field}字段应为字符串类型")
    
    def _is_valid_time_format(self, time_str):
        """
        检查时间格式是否有效
        
        Args:
            time_str (str): 时间字符串
            
        Returns:
            bool: 是否为有效格式
        """
        # 支持的时间格式
        time_formats = [
            "%Y-%m-%d %H:%M:%S",  # 2023-01-01 12:00:00
            "%Y-%m-%d %H:%M",     # 2023-01-01 12:00
            "%Y/%m/%d %H:%M:%S",  # 2023/01/01 12:00:00
            "%Y/%m/%d %H:%M",     # 2023/01/01 12:00
            "%Y-%m-%d",           # 2023-01-01
            "%Y/%m/%d"            # 2023/01/01
        ]
        
        for fmt in time_formats:
            try:
                datetime.strptime(time_str, fmt)
                return True
            except ValueError:
                continue
        
        return False
    
    def detect_missing_fields(self, data):
        """
        检测缺失必需字段的功能
        
        Args:
            data (dict): 数据对象
            
        Returns:
            list: 缺失字段的详细信息列表
        """
        missing_fields = []
        
        # 检查info字段
        if "info" in data and isinstance(data["info"], dict):
            info = data["info"]
            for field in self.required_info_fields:
                if field not in info or not info[field] or str(info[field]).strip() == "":
                    missing_fields.append({
                        "type": "info",
                        "field": field,
                        "location": "info字段"
                    })
        
        # 检查记录字段
        if "list" in data and isinstance(data["list"], list):
            for i, record in enumerate(data["list"]):
                if isinstance(record, dict):
                    for field in self.required_record_fields:
                        if field not in record or (field in ["gacha_type", "time", "id"] and 
                                                 (not record[field] or str(record[field]).strip() == "")):
                            missing_fields.append({
                                "type": "record",
                                "field": field,
                                "location": f"第{i+1}条记录",
                                "record_index": i
                            })
        
        return missing_fields
    
    def detect_invalid_data_types(self, data):
        """
        检测无效数据类型的功能
        
        Args:
            data (dict): 数据对象
            
        Returns:
            list: 无效数据类型的详细信息列表
        """
        invalid_types = []
        
        # 检查info字段数据类型
        if "info" in data and isinstance(data["info"], dict):
            info = data["info"]
            for field in self.required_info_fields:
                if field in info and info[field] is not None and not isinstance(info[field], str):
                    invalid_types.append({
                        "type": "info",
                        "field": field,
                        "location": "info字段",
                        "current_type": type(info[field]).__name__,
                        "expected_type": "str"
                    })
        
        # 检查记录字段数据类型
        if "list" in data and isinstance(data["list"], list):
            string_fields = ["gacha_type", "time", "name", "item_type", "rank_type", "id", "uid", "lang", "item_id", "count"]
            
            for i, record in enumerate(data["list"]):
                if isinstance(record, dict):
                    for field in string_fields:
                        if field in record and record[field] is not None and not isinstance(record[field], str):
                            invalid_types.append({
                                "type": "record",
                                "field": field,
                                "location": f"第{i+1}条记录",
                                "record_index": i,
                                "current_type": type(record[field]).__name__,
                                "expected_type": "str"
                            })
        
        return invalid_types
    
    def detect_duplicate_ids(self, data):
        """
        检测重复id字段的功能
        
        Args:
            data (dict): 数据对象
            
        Returns:
            list: 重复ID的详细信息列表
        """
        duplicates = []
        
        if "list" not in data or not isinstance(data["list"], list):
            return duplicates
        
        id_locations = {}  # id -> [record_indices]
        
        for i, record in enumerate(data["list"]):
            if isinstance(record, dict) and "id" in record and record["id"]:
                record_id = str(record["id"])
                if record_id not in id_locations:
                    id_locations[record_id] = []
                id_locations[record_id].append(i)
        
        # 找出重复的ID
        for record_id, indices in id_locations.items():
            if len(indices) > 1:
                duplicates.append({
                    "id": record_id,
                    "locations": [f"第{i+1}条记录" for i in indices],
                    "record_indices": indices
                })
        
        return duplicates
    
    def detect_time_format_errors(self, data):
        """
        检测时间格式错误的功能
        
        Args:
            data (dict): 数据对象
            
        Returns:
            list: 时间格式错误的详细信息列表
        """
        time_errors = []
        
        if "list" not in data or not isinstance(data["list"], list):
            return time_errors
        
        for i, record in enumerate(data["list"]):
            if isinstance(record, dict) and "time" in record and record["time"]:
                time_str = str(record["time"])
                if not self._is_valid_time_format(time_str):
                    time_errors.append({
                        "location": f"第{i+1}条记录",
                        "record_index": i,
                        "invalid_time": time_str,
                        "field": "time"
                    })
        
        return time_errors
    
    def fix_missing_fields(self, record, default_values, record_index=None):
        """
        修复缺失字段
        
        Args:
            record (dict): 记录对象
            default_values (dict): 默认值字典
            record_index (int): 记录索引（用于生成默认ID）
            
        Returns:
            tuple: (fixed_record, fixes_applied)
                   fixed_record (dict): 修复后的记录
                   fixes_applied (list): 应用的修复列表
        """
        fixed_record = record.copy()
        fixes_applied = []
        
        # 修复缺失的必需字段
        for field in self.required_record_fields:
            if field not in fixed_record or not fixed_record[field] or str(fixed_record[field]).strip() == "":
                if field in default_values:
                    fixed_record[field] = default_values[field]
                    fixes_applied.append(f"添加缺失字段 {field}: {default_values[field]}")
                else:
                    # 使用智能默认值
                    default_value = self._get_smart_default_value(field, fixed_record, record_index)
                    if default_value is not None:
                        fixed_record[field] = default_value
                        fixes_applied.append(f"添加缺失字段 {field}: {default_value}")
        
        # 确保可选字段也有合理的默认值
        optional_fields = ["uid", "lang", "item_id", "count"]
        for field in optional_fields:
            if field not in fixed_record or not fixed_record[field]:
                if field in default_values:
                    fixed_record[field] = default_values[field]
                    fixes_applied.append(f"添加可选字段 {field}: {default_values[field]}")
                else:
                    default_value = self._get_smart_default_value(field, fixed_record, record_index)
                    if default_value is not None:
                        fixed_record[field] = default_value
                        fixes_applied.append(f"添加可选字段 {field}: {default_value}")
        
        return fixed_record, fixes_applied
    
    def fix_data_types(self, record):
        """
        修复数据类型错误
        
        Args:
            record (dict): 记录对象
            
        Returns:
            tuple: (fixed_record, fixes_applied)
                   fixed_record (dict): 修复后的记录
                   fixes_applied (list): 应用的修复列表
        """
        fixed_record = record.copy()
        fixes_applied = []
        
        # 应该是字符串的字段
        string_fields = ["gacha_type", "time", "name", "item_type", "rank_type", "id", "uid", "lang", "item_id", "count"]
        
        for field in string_fields:
            if field in fixed_record and fixed_record[field] is not None:
                if not isinstance(fixed_record[field], str):
                    old_value = fixed_record[field]
                    old_type = type(old_value).__name__
                    
                    # 转换为字符串
                    try:
                        fixed_record[field] = str(old_value)
                        fixes_applied.append(f"转换字段 {field} 从 {old_type} 到 str: {old_value} -> {fixed_record[field]}")
                    except Exception as e:
                        # 如果转换失败，使用默认值
                        default_value = self._get_smart_default_value(field, fixed_record)
                        if default_value is not None:
                            fixed_record[field] = default_value
                            fixes_applied.append(f"转换字段 {field} 失败，使用默认值: {default_value}")
        
        return fixed_record, fixes_applied
    
    def fix_time_format(self, time_str):
        """
        修复时间格式
        
        Args:
            time_str (str): 时间字符串
            
        Returns:
            tuple: (fixed_time, success)
                   fixed_time (str): 修复后的时间字符串
                   success (bool): 是否修复成功
        """
        if not time_str or not isinstance(time_str, str):
            return "2023-01-01 00:00:00", False
        
        time_str = time_str.strip()
        
        # 如果已经是有效格式，直接返回
        if self._is_valid_time_format(time_str):
            return time_str, True
        
        # 尝试各种修复策略
        
        # 1. 尝试解析时间戳
        try:
            # Unix时间戳（秒）
            if time_str.isdigit() and len(time_str) == 10:
                timestamp = int(time_str)
                dt = datetime.fromtimestamp(timestamp)
                return dt.strftime("%Y-%m-%d %H:%M:%S"), True
            
            # Unix时间戳（毫秒）
            if time_str.isdigit() and len(time_str) == 13:
                timestamp = int(time_str) / 1000
                dt = datetime.fromtimestamp(timestamp)
                return dt.strftime("%Y-%m-%d %H:%M:%S"), True
        except (ValueError, OSError):
            pass
        
        # 2. 尝试常见的错误格式修复
        
        # 修复日期分隔符
        time_str = re.sub(r'[/\\.]', '-', time_str)
        
        # 修复时间分隔符
        time_str = re.sub(r'[：]', ':', time_str)
        
        # 移除多余的空格
        time_str = re.sub(r'\s+', ' ', time_str)
        
        # 尝试匹配和修复常见格式
        patterns = [
            # 2023-1-1 12:0:0 -> 2023-01-01 12:00:00
            (r'(\d{4})-(\d{1,2})-(\d{1,2})\s+(\d{1,2}):(\d{1,2}):(\d{1,2})', 
             lambda m: f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)} {m.group(4).zfill(2)}:{m.group(5).zfill(2)}:{m.group(6).zfill(2)}"),
            
            # 2023-1-1 12:0 -> 2023-01-01 12:00:00
            (r'(\d{4})-(\d{1,2})-(\d{1,2})\s+(\d{1,2}):(\d{1,2})', 
             lambda m: f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)} {m.group(4).zfill(2)}:{m.group(5).zfill(2)}:00"),
            
            # 2023-1-1 -> 2023-01-01 00:00:00
            (r'(\d{4})-(\d{1,2})-(\d{1,2})$', 
             lambda m: f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)} 00:00:00"),
        ]
        
        for pattern, replacement in patterns:
            match = re.match(pattern, time_str)
            if match:
                try:
                    fixed_time = replacement(match)
                    if self._is_valid_time_format(fixed_time):
                        return fixed_time, True
                except Exception:
                    continue
        
        # 3. 如果所有修复尝试都失败，返回默认时间
        return "2023-01-01 00:00:00", False
    
    def remove_duplicates(self, records):
        """
        根据id字段去重
        
        Args:
            records (list): 记录列表
            
        Returns:
            tuple: (unique_records, removed_count)
                   unique_records (list): 去重后的记录列表
                   removed_count (int): 移除的重复记录数量
        """
        if not records:
            return [], 0
        
        seen_ids = set()
        unique_records = []
        removed_count = 0
        
        for record in records:
            if not isinstance(record, dict) or "id" not in record or not record["id"]:
                # 没有ID的记录保留
                unique_records.append(record)
                continue
            
            record_id = str(record["id"])
            
            if record_id not in seen_ids:
                seen_ids.add(record_id)
                unique_records.append(record)
            else:
                removed_count += 1
        
        return unique_records, removed_count
    
    def _get_smart_default_value(self, field, record, record_index=None):
        """
        获取字段的智能默认值
        
        Args:
            field (str): 字段名
            record (dict): 记录对象
            record_index (int): 记录索引
            
        Returns:
            str: 默认值，如果无法确定则返回None
        """
        # 根据字段类型提供智能默认值
        if field == "gacha_type":
            # 使用游戏的第一个有效gacha_type
            return self.gacha_types[0] if self.gacha_types else "100"
        
        elif field == "time":
            return "2023-01-01 00:00:00"
        
        elif field == "name":
            return "未知物品"
        
        elif field == "item_type":
            return "未知类型"
        
        elif field == "rank_type":
            return "3"  # 默认3星
        
        elif field == "id":
            # 生成一个基于索引的ID
            if record_index is not None:
                return str(1000000000 + record_index)
            else:
                import time
                return str(int(time.time() * 1000))  # 使用时间戳
        
        elif field == "uid":
            return "000000000"  # 默认UID
        
        elif field == "lang":
            return "zh-cn"
        
        elif field == "item_id":
            return "0"
        
        elif field == "count":
            return "1"
        
        return None 
   
    def generate_repair_report(self, issues_found, issues_fixed):
        """
        生成修复报告
        
        Args:
            issues_found (dict): 发现的问题
            issues_fixed (dict): 修复的问题
            
        Returns:
            str: 修复报告文本
        """
        report_lines = []
        report_lines.append("=" * 60)
        report_lines.append("UIGF/SRGF 文件修复报告")
        report_lines.append("=" * 60)
        report_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"游戏类型: {self.format_info['format_name'] if self.format_info else '未知'}")
        report_lines.append("")
        
        # 统计信息
        total_issues_found = sum(len(issues) for issues in issues_found.values())
        total_issues_fixed = sum(len(fixes) for fixes in issues_fixed.values())
        
        report_lines.append("修复统计:")
        report_lines.append(f"  发现问题总数: {total_issues_found}")
        report_lines.append(f"  成功修复数量: {total_issues_fixed}")
        report_lines.append(f"  修复成功率: {(total_issues_fixed/total_issues_found*100):.1f}%" if total_issues_found > 0 else "  修复成功率: 100.0%")
        report_lines.append("")
        
        # 详细问题报告
        if issues_found["file_errors"]:
            report_lines.append("文件错误:")
            for error in issues_found["file_errors"]:
                report_lines.append(f"  ❌ {error}")
            report_lines.append("")
        
        if issues_found["structure_errors"]:
            report_lines.append("结构错误:")
            for error in issues_found["structure_errors"]:
                report_lines.append(f"  ❌ {error}")
            report_lines.append("")
        
        if issues_found["info_errors"]:
            report_lines.append("Info字段错误:")
            for error in issues_found["info_errors"]:
                report_lines.append(f"  ❌ {error}")
            report_lines.append("")
        
        if issues_found["record_errors"]:
            report_lines.append("记录字段错误:")
            for error in issues_found["record_errors"]:
                report_lines.append(f"  ❌ {error}")
            report_lines.append("")
        
        if issues_found["duplicate_ids"]:
            report_lines.append("重复ID:")
            for dup in issues_found["duplicate_ids"]:
                report_lines.append(f"  ❌ ID '{dup}' 出现多次")
            report_lines.append("")
        
        if issues_found["time_format_errors"]:
            report_lines.append("时间格式错误:")
            for error in issues_found["time_format_errors"]:
                report_lines.append(f"  ❌ {error}")
            report_lines.append("")
        
        if issues_found["data_type_errors"]:
            report_lines.append("数据类型错误:")
            for error in issues_found["data_type_errors"]:
                report_lines.append(f"  ❌ {error}")
            report_lines.append("")
        
        # 修复详情
        if any(issues_fixed.values()):
            report_lines.append("修复详情:")
            
            if issues_fixed["missing_fields"]:
                report_lines.append("  缺失字段修复:")
                for fix in issues_fixed["missing_fields"]:
                    report_lines.append(f"    ✅ {fix}")
                report_lines.append("")
            
            if issues_fixed["data_types"]:
                report_lines.append("  数据类型修复:")
                for fix in issues_fixed["data_types"]:
                    report_lines.append(f"    ✅ {fix}")
                report_lines.append("")
            
            if issues_fixed["time_formats"]:
                report_lines.append("  时间格式修复:")
                for fix in issues_fixed["time_formats"]:
                    report_lines.append(f"    ✅ {fix}")
                report_lines.append("")
            
            if issues_fixed["duplicates"]:
                report_lines.append("  重复记录处理:")
                for fix in issues_fixed["duplicates"]:
                    report_lines.append(f"    ✅ {fix}")
                report_lines.append("")
        
        # 无法修复的问题
        unfixable_issues = []
        if issues_found["file_errors"]:
            unfixable_issues.extend(issues_found["file_errors"])
        if issues_found["structure_errors"]:
            unfixable_issues.extend(issues_found["structure_errors"])
        
        if unfixable_issues:
            report_lines.append("无法自动修复的问题:")
            for issue in unfixable_issues:
                report_lines.append(f"  ⚠️  {issue}")
            report_lines.append("")
            report_lines.append("建议:")
            report_lines.append("  - 检查原始文件是否损坏")
            report_lines.append("  - 确认文件格式是否正确")
            report_lines.append("  - 联系数据提供方获取正确格式的文件")
            report_lines.append("")
        
        report_lines.append("=" * 60)
        
        return "\n".join(report_lines)
    
    def repair_file(self, file_path, output_dir, progress_callback=None):
        """
        修复文件并生成修复报告
        
        Args:
            file_path (str): 输入文件路径
            output_dir (str): 输出目录路径
            progress_callback (callable): 进度回调函数
            
        Returns:
            tuple: (success, error_message, repair_info)
                   success (bool): 是否成功
                   error_message (str): 错误信息
                   repair_info (dict): 修复信息
        """
        try:
            # 确保输出目录存在
            success, error_msg = create_output_directory(output_dir)
            if not success:
                return False, f"无法创建输出目录: {error_msg}", None
            
            if progress_callback:
                progress_callback(10, 100, "正在分析文件问题...")
            
            # 分析文件问题
            issues_found, data = self.analyze_file_issues(file_path)
            
            if data is None:
                # 生成详细的错误报告
                error_report = self._generate_error_report(issues_found, file_path)
                return False, "无法加载文件数据，请检查文件格式", {
                    "report": error_report,
                    "issues_found": issues_found,
                    "unfixable_errors": issues_found.get("file_errors", []) + issues_found.get("structure_errors", [])
                }
            
            # 检查是否存在无法修复的严重错误
            unfixable_errors = []
            if issues_found["file_errors"]:
                unfixable_errors.extend(issues_found["file_errors"])
            if issues_found["structure_errors"]:
                unfixable_errors.extend(issues_found["structure_errors"])
            
            if unfixable_errors:
                # 生成包含无法修复错误的详细报告
                error_report = self._generate_error_report(issues_found, file_path)
                return False, self._format_unfixable_error_message(unfixable_errors), {
                    "report": error_report,
                    "issues_found": issues_found,
                    "unfixable_errors": unfixable_errors
                }
            
            if progress_callback:
                progress_callback(30, 100, "正在修复文件问题...")
            
            # 开始修复
            issues_fixed = {
                "missing_fields": [],
                "data_types": [],
                "time_formats": [],
                "duplicates": []
            }
            
            try:
                # 修复info字段
                if "info" in data:
                    data["info"] = self._fix_info_fields(data["info"], issues_fixed)
                
                if progress_callback:
                    progress_callback(50, 100, "正在修复记录数据...")
                
                # 修复记录
                if "list" in data and isinstance(data["list"], list):
                    data["list"] = self._fix_records(data["list"], issues_fixed, progress_callback)
                
            except Exception as e:
                # 修复过程中出现错误
                error_msg = f"修复过程中发生错误: {str(e)}"
                partial_report = self.generate_repair_report(issues_found, issues_fixed)
                return False, error_msg, {
                    "report": partial_report,
                    "issues_found": issues_found,
                    "issues_fixed": issues_fixed,
                    "repair_error": str(e)
                }
            
            if progress_callback:
                progress_callback(80, 100, "正在保存修复后的文件...")
            
            # 保存修复后的文件
            original_filename = os.path.splitext(os.path.basename(file_path))[0]
            repaired_filename = f"{original_filename}_repaired.json"
            repaired_file_path = os.path.join(output_dir, repaired_filename)
            
            try:
                with open(repaired_file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2, separators=(',', ': '))
            except Exception as e:
                error_msg = f"保存修复后文件时发生错误: {str(e)}"
                return False, error_msg, {
                    "issues_found": issues_found,
                    "issues_fixed": issues_fixed,
                    "save_error": str(e)
                }
            
            # 验证文件是否成功保存
            if not os.path.exists(repaired_file_path):
                return False, f"修复后文件保存失败: {repaired_file_path}", None
            
            if progress_callback:
                progress_callback(90, 100, "正在生成修复报告...")
            
            # 生成修复报告
            repair_report = self.generate_repair_report(issues_found, issues_fixed)
            
            # 保存修复报告
            report_filename = f"{original_filename}_repair_report.txt"
            report_file_path = os.path.join(output_dir, report_filename)
            
            try:
                with open(report_file_path, 'w', encoding='utf-8') as f:
                    f.write(repair_report)
            except Exception as e:
                # 报告保存失败不影响修复成功
                pass
            
            if progress_callback:
                progress_callback(100, 100, "修复完成")
            
            # 计算修复统计信息
            total_issues = sum(len(issues) for issues in issues_found.values())
            total_fixed = sum(len(fixes) for fixes in issues_fixed.values())
            
            repair_info = {
                "repaired_file": repaired_file_path,
                "report_file": report_file_path if os.path.exists(report_file_path) else None,
                "report": repair_report,
                "issues_found": issues_found,
                "issues_fixed": issues_fixed,
                "total_issues": total_issues,
                "total_fixed": total_fixed,
                "success_rate": (total_fixed / total_issues * 100) if total_issues > 0 else 100.0
            }
            
            return True, None, repair_info
            
        except PermissionError as e:
            return False, f"权限不足，无法访问文件或目录: {str(e)}", None
        except FileNotFoundError as e:
            return False, f"文件不存在: {str(e)}", None
        except Exception as e:
            return False, f"修复文件时发生未知错误: {str(e)}", None
    
    def _generate_error_report(self, issues_found, file_path):
        """
        生成错误报告（用于无法修复的情况）
        
        Args:
            issues_found (dict): 发现的问题
            file_path (str): 文件路径
            
        Returns:
            str: 错误报告文本
        """
        report_lines = []
        report_lines.append("=" * 60)
        report_lines.append("UIGF/SRGF 文件错误分析报告")
        report_lines.append("=" * 60)
        report_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"文件路径: {file_path}")
        report_lines.append(f"游戏类型: {self.format_info['format_name'] if self.format_info else '未知'}")
        report_lines.append("")
        
        # 统计信息
        total_issues = sum(len(issues) for issues in issues_found.values())
        report_lines.append(f"检测到问题总数: {total_issues}")
        report_lines.append("")
        
        # 严重错误（无法修复）
        if issues_found["file_errors"]:
            report_lines.append("严重文件错误（无法自动修复）:")
            for error in issues_found["file_errors"]:
                report_lines.append(f"  ❌ {error}")
            report_lines.append("")
        
        if issues_found["structure_errors"]:
            report_lines.append("严重结构错误（无法自动修复）:")
            for error in issues_found["structure_errors"]:
                report_lines.append(f"  ❌ {error}")
            report_lines.append("")
        
        # 其他问题（可能可以修复）
        if issues_found["info_errors"]:
            report_lines.append("Info字段问题:")
            for error in issues_found["info_errors"]:
                report_lines.append(f"  ⚠️  {error}")
            report_lines.append("")
        
        if issues_found["record_errors"]:
            report_lines.append("记录字段问题:")
            for error in issues_found["record_errors"]:
                report_lines.append(f"  ⚠️  {error}")
            report_lines.append("")
        
        if issues_found["duplicate_ids"]:
            report_lines.append("重复ID问题:")
            for dup in issues_found["duplicate_ids"]:
                report_lines.append(f"  ⚠️  {dup}")
            report_lines.append("")
        
        if issues_found["time_format_errors"]:
            report_lines.append("时间格式问题:")
            for error in issues_found["time_format_errors"]:
                report_lines.append(f"  ⚠️  {error}")
            report_lines.append("")
        
        if issues_found["data_type_errors"]:
            report_lines.append("数据类型问题:")
            for error in issues_found["data_type_errors"]:
                report_lines.append(f"  ⚠️  {error}")
            report_lines.append("")
        
        # 修复建议
        report_lines.append("修复建议:")
        if issues_found["file_errors"] or issues_found["structure_errors"]:
            report_lines.append("  由于存在严重的文件或结构错误，建议:")
            report_lines.append("  1. 检查原始文件是否完整且未损坏")
            report_lines.append("  2. 确认文件确实是UIGF/SRGF格式")
            report_lines.append("  3. 检查文件编码是否为UTF-8")
            report_lines.append("  4. 联系数据提供方获取正确格式的文件")
        else:
            report_lines.append("  文件基本结构正常，但存在格式问题")
            report_lines.append("  建议使用修复功能尝试自动修复")
        
        report_lines.append("")
        report_lines.append("=" * 60)
        
        return "\n".join(report_lines)
    
    def _format_unfixable_error_message(self, unfixable_errors):
        """
        格式化无法修复的错误消息
        
        Args:
            unfixable_errors (list): 无法修复的错误列表
            
        Returns:
            str: 格式化的错误消息
        """
        if not unfixable_errors:
            return "文件存在无法修复的错误"
        
        error_msg = "文件存在以下无法自动修复的严重错误:\n\n"
        
        for i, error in enumerate(unfixable_errors, 1):
            error_msg += f"{i}. {error}\n"
        
        error_msg += "\n建议解决方案:\n"
        error_msg += "• 检查原始文件是否完整且未损坏\n"
        error_msg += "• 确认文件格式是否正确（UIGF/SRGF）\n"
        error_msg += "• 检查文件编码是否为UTF-8\n"
        error_msg += "• 联系数据提供方获取正确格式的文件"
        
        return error_msg
    
    def _fix_info_fields(self, info, issues_fixed):
        """
        修复info字段中的问题
        
        Args:
            info (dict): info字段数据
            issues_fixed (dict): 修复记录字典
            
        Returns:
            dict: 修复后的info字段
        """
        fixed_info = info.copy()
        
        # 修复缺失的必需字段
        for field in self.required_info_fields:
            if field not in fixed_info or not fixed_info[field] or str(fixed_info[field]).strip() == "":
                default_value = self._get_info_default_value(field)
                if default_value is not None:
                    fixed_info[field] = default_value
                    issues_fixed["missing_fields"].append(f"info字段添加缺失的{field}: {default_value}")
        
        # 修复数据类型错误
        for field in self.required_info_fields:
            if field in fixed_info and fixed_info[field] is not None:
                if not isinstance(fixed_info[field], str):
                    old_value = fixed_info[field]
                    old_type = type(old_value).__name__
                    try:
                        fixed_info[field] = str(old_value)
                        issues_fixed["data_types"].append(f"info字段{field}从{old_type}转换为str: {old_value} -> {fixed_info[field]}")
                    except Exception:
                        # 转换失败，使用默认值
                        default_value = self._get_info_default_value(field)
                        if default_value is not None:
                            fixed_info[field] = default_value
                            issues_fixed["data_types"].append(f"info字段{field}转换失败，使用默认值: {default_value}")
        
        return fixed_info
    
    def _fix_records(self, records, issues_fixed, progress_callback=None):
        """
        修复记录列表中的问题
        
        Args:
            records (list): 记录列表
            issues_fixed (dict): 修复记录字典
            progress_callback (callable): 进度回调函数
            
        Returns:
            list: 修复后的记录列表
        """
        if not records:
            return records
        
        fixed_records = []
        total_records = len(records)
        
        # 第一步：修复各种字段问题
        for i, record in enumerate(records):
            if progress_callback and i % 100 == 0:  # 每100条记录更新一次进度
                progress = 50 + (i / total_records) * 20  # 50-70%的进度
                progress_callback(int(progress), 100, f"修复记录 {i+1}/{total_records}...")
            
            if not isinstance(record, dict):
                # 跳过非字典类型的记录
                continue
            
            fixed_record = record.copy()
            
            # 修复缺失字段
            fixed_record, missing_fixes = self.fix_missing_fields(fixed_record, {}, i)
            issues_fixed["missing_fields"].extend(missing_fixes)
            
            # 修复数据类型
            fixed_record, type_fixes = self.fix_data_types(fixed_record)
            issues_fixed["data_types"].extend(type_fixes)
            
            # 修复时间格式
            if "time" in fixed_record and fixed_record["time"]:
                original_time = fixed_record["time"]
                fixed_time, success = self.fix_time_format(str(original_time))
                if not success or fixed_time != original_time:
                    fixed_record["time"] = fixed_time
                    if success:
                        issues_fixed["time_formats"].append(f"第{i+1}条记录时间格式修复: {original_time} -> {fixed_time}")
                    else:
                        issues_fixed["time_formats"].append(f"第{i+1}条记录时间格式无法修复，使用默认值: {original_time} -> {fixed_time}")
            
            fixed_records.append(fixed_record)
        
        # 第二步：去重处理
        if progress_callback:
            progress_callback(70, 100, "处理重复记录...")
        
        unique_records, removed_count = self.remove_duplicates(fixed_records)
        if removed_count > 0:
            issues_fixed["duplicates"].append(f"移除重复记录: {removed_count} 条")
        
        return unique_records
    
    def _get_info_default_value(self, field):
        """
        获取info字段的默认值
        
        Args:
            field (str): 字段名
            
        Returns:
            str: 默认值
        """
        if field == "uid":
            return "000000000"
        elif field == "lang":
            return "zh-cn"
        elif field == "export_time":
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        elif field == "uigf_version":
            return "v3.0"
        elif field == "srgf_version":
            return "v1.0"
        else:
            return ""
    
    def _fix_info_fields(self, info, issues_fixed):
        """
        修复info字段
        
        Args:
            info (dict): info字段数据
            issues_fixed (dict): 修复记录
            
        Returns:
            dict: 修复后的info字段
        """
        fixed_info = info.copy()
        
        # 修复缺失字段
        default_values = {
            "uid": "000000000",
            "lang": "zh-cn",
            "export_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 添加游戏特定的版本字段默认值
        if self.format_info:
            version_field = self.format_info["version_field"]
            if self.game_type == "genshin":
                default_values[version_field] = "v3.0"
            elif self.game_type == "starrail":
                default_values[version_field] = "v1.0"
        
        for field in self.required_info_fields:
            if field not in fixed_info or not fixed_info[field] or str(fixed_info[field]).strip() == "":
                if field in default_values:
                    fixed_info[field] = default_values[field]
                    issues_fixed["missing_fields"].append(f"info.{field}: 添加默认值 '{default_values[field]}'")
        
        # 修复数据类型
        for field in self.required_info_fields:
            if field in fixed_info and fixed_info[field] is not None and not isinstance(fixed_info[field], str):
                old_value = fixed_info[field]
                fixed_info[field] = str(old_value)
                issues_fixed["data_types"].append(f"info.{field}: 转换为字符串 '{old_value}' -> '{fixed_info[field]}'")
        
        return fixed_info
    
    def _fix_records(self, records, issues_fixed, progress_callback=None):
        """
        修复记录列表
        
        Args:
            records (list): 记录列表
            issues_fixed (dict): 修复记录
            progress_callback (callable): 进度回调
            
        Returns:
            list: 修复后的记录列表
        """
        if not records:
            return records
        
        # 首先去重
        unique_records, removed_count = self.remove_duplicates(records)
        if removed_count > 0:
            issues_fixed["duplicates"].append(f"移除了 {removed_count} 条重复记录")
        
        # 修复每条记录
        fixed_records = []
        total_records = len(unique_records)
        
        # 从第一条有效记录中提取默认值
        default_uid = extract_uid_from_data({"list": unique_records}) or "000000000"
        
        for i, record in enumerate(unique_records):
            if not isinstance(record, dict):
                continue
            
            # 准备默认值
            default_values = {
                "uid": default_uid,
                "lang": "zh-cn",
                "count": "1"
            }
            
            # 修复缺失字段
            fixed_record, field_fixes = self.fix_missing_fields(record, default_values, i)
            issues_fixed["missing_fields"].extend(field_fixes)
            
            # 修复数据类型
            fixed_record, type_fixes = self.fix_data_types(fixed_record)
            issues_fixed["data_types"].extend(type_fixes)
            
            # 修复时间格式
            if "time" in fixed_record and fixed_record["time"]:
                original_time = fixed_record["time"]
                fixed_time, success = self.fix_time_format(original_time)
                if not success or fixed_time != original_time:
                    fixed_record["time"] = fixed_time
                    issues_fixed["time_formats"].append(f"第{i+1}条记录: '{original_time}' -> '{fixed_time}'")
            
            fixed_records.append(fixed_record)
            
            # 更新进度
            if progress_callback and (i + 1) % 100 == 0:
                progress = 50 + int((i + 1) / total_records * 30)  # 50-80%的进度范围
                message = format_progress_message(i + 1, total_records, "修复")
                progress_callback(progress, 100, message)
        
        return fixed_records