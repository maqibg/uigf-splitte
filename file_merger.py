#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UIGF/SRGF 抽卡记录分离工具 - 文件合并器模块
提供UIGF/SRGF格式文件的合并功能

by: 马乞
GitHub: https://github.com/maqibg/yunzai-uigf-splitte
"""

import json
import os
from game_config import GameConfig
from utils import validate_json_structure, create_output_directory, extract_uid_from_data, compare_records_by_id, sanitize_filename, format_progress_message


class FileMerger:
    """文件合并器类，负责合并两个相同UID的UIGF/SRGF格式文件"""
    
    def __init__(self, game_type):
        """
        初始化文件合并器
        
        Args:
            game_type (str): 游戏类型 ("genshin" 或 "starrail")
        """
        self.game_type = game_type
        self.gacha_types = GameConfig.get_gacha_types(game_type)
        self.format_info = GameConfig.get_file_format_info(game_type)
        
        if not self.gacha_types:
            raise ValueError(f"不支持的游戏类型: {game_type}")
    
    def validate_merge_files(self, file1_path, file2_path):
        """
        验证两个文件是否可以合并（相同UID）
        
        Args:
            file1_path (str): 第一个文件路径
            file2_path (str): 第二个文件路径
            
        Returns:
            tuple: (is_valid, error_message, uid, error_details)
                   is_valid (bool): 是否可以合并
                   error_message (str): 错误信息，如果可以合并则为None
                   uid (str): 共同的UID，如果验证失败则为None
                   error_details (dict): 详细错误信息
        """
        error_details = {
            "error_type": None,
            "file1_issues": [],
            "file2_issues": [],
            "compatibility_issues": []
        }
        
        try:
            # 检查文件是否存在
            if not os.path.exists(file1_path):
                error_details["error_type"] = "file_not_found"
                error_details["file1_issues"].append("文件不存在")
                return False, f"第一个文件不存在: {file1_path}", None, error_details
            
            if not os.path.exists(file2_path):
                error_details["error_type"] = "file_not_found"
                error_details["file2_issues"].append("文件不存在")
                return False, f"第二个文件不存在: {file2_path}", None, error_details
            
            # 检查是否为同一个文件
            if os.path.abspath(file1_path) == os.path.abspath(file2_path):
                error_details["error_type"] = "same_file"
                error_details["compatibility_issues"].append("选择了同一个文件")
                return False, "不能选择同一个文件进行合并", None, error_details
            
            # 检查文件是否可读
            if not os.access(file1_path, os.R_OK):
                error_details["error_type"] = "permission_error"
                error_details["file1_issues"].append("文件不可读，权限不足")
                return False, f"第一个文件不可读，请检查文件权限: {file1_path}", None, error_details
            
            if not os.access(file2_path, os.R_OK):
                error_details["error_type"] = "permission_error"
                error_details["file2_issues"].append("文件不可读，权限不足")
                return False, f"第二个文件不可读，请检查文件权限: {file2_path}", None, error_details
            
            # 检查文件大小是否合理
            try:
                file1_size = os.path.getsize(file1_path)
                file2_size = os.path.getsize(file2_path)
                
                if file1_size == 0:
                    error_details["error_type"] = "empty_file"
                    error_details["file1_issues"].append("文件为空")
                    return False, "第一个文件为空", None, error_details
                
                if file2_size == 0:
                    error_details["error_type"] = "empty_file"
                    error_details["file2_issues"].append("文件为空")
                    return False, "第二个文件为空", None, error_details
                
                # 检查文件大小是否过大（超过100MB）
                max_size = 100 * 1024 * 1024  # 100MB
                if file1_size > max_size:
                    error_details["error_type"] = "file_too_large"
                    error_details["file1_issues"].append(f"文件过大 ({file1_size // (1024*1024)}MB)")
                    return False, f"第一个文件过大 ({file1_size // (1024*1024)}MB)，可能不是有效的抽卡记录文件", None, error_details
                
                if file2_size > max_size:
                    error_details["error_type"] = "file_too_large"
                    error_details["file2_issues"].append(f"文件过大 ({file2_size // (1024*1024)}MB)")
                    return False, f"第二个文件过大 ({file2_size // (1024*1024)}MB)，可能不是有效的抽卡记录文件", None, error_details
                    
            except OSError as e:
                error_details["error_type"] = "file_access_error"
                return False, f"无法访问文件信息: {str(e)}", None, error_details
            
            # 加载第一个文件
            data1 = None
            try:
                with open(file1_path, 'r', encoding='utf-8') as f:
                    data1 = json.load(f)
            except json.JSONDecodeError as e:
                error_details["error_type"] = "json_format_error"
                line_info = ""
                if hasattr(e, 'lineno') and hasattr(e, 'colno'):
                    line_info = f" (第{e.lineno}行，第{e.colno}列)"
                error_msg = f"JSON格式错误{line_info}: {e.msg}"
                error_details["file1_issues"].append(error_msg)
                return False, f"第一个文件{error_msg}", None, error_details
            except UnicodeDecodeError as e:
                error_details["error_type"] = "encoding_error"
                error_details["file1_issues"].append("文件编码错误，不是UTF-8格式")
                return False, f"第一个文件编码错误，请确保文件使用UTF-8编码: {str(e)}", None, error_details
            except Exception as e:
                error_details["error_type"] = "file_read_error"
                error_details["file1_issues"].append(f"读取失败: {str(e)}")
                return False, f"读取第一个文件时发生错误: {str(e)}", None, error_details
            
            # 加载第二个文件
            data2 = None
            try:
                with open(file2_path, 'r', encoding='utf-8') as f:
                    data2 = json.load(f)
            except json.JSONDecodeError as e:
                error_details["error_type"] = "json_format_error"
                line_info = ""
                if hasattr(e, 'lineno') and hasattr(e, 'colno'):
                    line_info = f" (第{e.lineno}行，第{e.colno}列)"
                error_msg = f"JSON格式错误{line_info}: {e.msg}"
                error_details["file2_issues"].append(error_msg)
                return False, f"第二个文件{error_msg}", None, error_details
            except UnicodeDecodeError as e:
                error_details["error_type"] = "encoding_error"
                error_details["file2_issues"].append("文件编码错误，不是UTF-8格式")
                return False, f"第二个文件编码错误，请确保文件使用UTF-8编码: {str(e)}", None, error_details
            except Exception as e:
                error_details["error_type"] = "file_read_error"
                error_details["file2_issues"].append(f"读取失败: {str(e)}")
                return False, f"读取第二个文件时发生错误: {str(e)}", None, error_details
            
            # 验证第一个文件的JSON结构
            is_valid1, error_msg1 = validate_json_structure(data1, self.game_type)
            if not is_valid1:
                error_details["error_type"] = "format_incompatible"
                error_details["file1_issues"].append(f"格式不符合{self.format_info['format_name']}标准: {error_msg1}")
                return False, f"第一个文件格式错误: {error_msg1}", None, error_details
            
            # 验证第二个文件的JSON结构
            is_valid2, error_msg2 = validate_json_structure(data2, self.game_type)
            if not is_valid2:
                error_details["error_type"] = "format_incompatible"
                error_details["file2_issues"].append(f"格式不符合{self.format_info['format_name']}标准: {error_msg2}")
                return False, f"第二个文件格式错误: {error_msg2}", None, error_details
            
            # 提取两个文件的UID
            uid1 = extract_uid_from_data(data1)
            uid2 = extract_uid_from_data(data2)
            
            if not uid1:
                error_details["error_type"] = "uid_extraction_failed"
                error_details["file1_issues"].append("无法提取有效的UID")
                return False, "第一个文件中无法提取有效的UID", None, error_details
            
            if not uid2:
                error_details["error_type"] = "uid_extraction_failed"
                error_details["file2_issues"].append("无法提取有效的UID")
                return False, "第二个文件中无法提取有效的UID", None, error_details
            
            # 检查UID是否相同
            if uid1 != uid2:
                error_details["error_type"] = "uid_mismatch"
                error_details["compatibility_issues"].append(f"UID不匹配: 文件1({uid1}) vs 文件2({uid2})")
                detailed_error = self._format_uid_mismatch_error(uid1, uid2, file1_path, file2_path)
                return False, detailed_error, None, error_details
            
            # 检查游戏类型兼容性
            game_type_compatible, game_error = self._check_game_type_compatibility(data1, data2)
            if not game_type_compatible:
                error_details["error_type"] = "game_type_incompatible"
                error_details["compatibility_issues"].append(game_error)
                return False, f"游戏类型不兼容: {game_error}", None, error_details
            
            # 检查记录数量是否合理
            records1 = data1.get("list", [])
            records2 = data2.get("list", [])
            
            if not isinstance(records1, list):
                error_details["error_type"] = "invalid_record_format"
                error_details["file1_issues"].append("记录列表格式错误，应为数组")
                return False, "第一个文件中的记录列表格式错误", None, error_details
            
            if not isinstance(records2, list):
                error_details["error_type"] = "invalid_record_format"
                error_details["file2_issues"].append("记录列表格式错误，应为数组")
                return False, "第二个文件中的记录列表格式错误", None, error_details
            
            total_records = len(records1) + len(records2)
            if total_records > 100000:  # 合理的记录数量上限
                error_details["error_type"] = "too_many_records"
                error_details["compatibility_issues"].append(f"合并后记录数量过多: {total_records}条")
                return False, f"合并后记录数量过多({total_records}条)，请确认这是正确的抽卡记录文件", None, error_details
            
            if total_records == 0:
                error_details["error_type"] = "no_records"
                error_details["compatibility_issues"].append("两个文件都没有抽卡记录")
                return False, "两个文件都没有抽卡记录，无法进行合并", None, error_details
            
            # 检查记录质量
            quality_issues = self._check_record_quality(records1, records2)
            if quality_issues:
                error_details["compatibility_issues"].extend(quality_issues)
                # 质量问题不阻止合并，只是警告
            
            return True, None, uid1, error_details
            
        except PermissionError as e:
            error_details["error_type"] = "permission_error"
            return False, f"权限不足，无法访问文件: {str(e)}", None, error_details
        except FileNotFoundError as e:
            error_details["error_type"] = "file_not_found"
            return False, f"文件不存在: {str(e)}", None, error_details
        except Exception as e:
            error_details["error_type"] = "unknown_error"
            return False, f"验证文件时发生未知错误: {str(e)}", None, error_details
    
    def merge_records(self, records1, records2):
        """
        合并两个记录列表，根据id字段识别重复记录并去重
        
        Args:
            records1 (list): 第一个文件的记录列表
            records2 (list): 第二个文件的记录列表
            
        Returns:
            tuple: (merged_records, stats)
                   merged_records (list): 合并后的记录列表
                   stats (dict): 合并统计信息
        """
        try:
            # 统计信息
            stats = {
                "file1_records": len(records1),
                "file2_records": len(records2),
                "duplicate_records": 0,
                "unique_records": 0,
                "total_merged_records": 0
            }
            
            # 使用字典来存储记录，以id为键进行去重
            merged_dict = {}
            
            # 处理第一个文件的记录
            for record in records1:
                if not isinstance(record, dict):
                    continue
                
                record_id = str(record.get("id", ""))
                if not record_id:
                    continue
                
                # 创建记录的副本以避免修改原始数据
                record_copy = record.copy()
                merged_dict[record_id] = record_copy
            
            # 处理第二个文件的记录
            for record in records2:
                if not isinstance(record, dict):
                    continue
                
                record_id = str(record.get("id", ""))
                if not record_id:
                    continue
                
                # 创建记录的副本
                record_copy = record.copy()
                
                if record_id in merged_dict:
                    # 发现重复记录，保留现有记录（第一个文件优先）
                    stats["duplicate_records"] += 1
                else:
                    # 独有记录，添加到合并结果中
                    merged_dict[record_id] = record_copy
            
            # 转换为列表
            merged_records = list(merged_dict.values())
            
            # 更新统计信息
            stats["unique_records"] = len(merged_records) - stats["duplicate_records"]
            stats["total_merged_records"] = len(merged_records)
            
            return merged_records, stats
            
        except Exception as e:
            # 如果合并过程中出现错误，返回空列表和错误统计
            error_stats = {
                "file1_records": len(records1) if isinstance(records1, list) else 0,
                "file2_records": len(records2) if isinstance(records2, list) else 0,
                "duplicate_records": 0,
                "unique_records": 0,
                "total_merged_records": 0,
                "error": str(e)
            }
            return [], error_stats
    
    def sort_records_by_id(self, records):
        """
        按id字段从小到大排序记录
        
        Args:
            records (list): 记录列表
            
        Returns:
            list: 排序后的记录列表
        """
        try:
            if not records:
                return records
            
            # 检查第一条记录来确定排序策略
            first_record = records[0]
            
            if 'id' in first_record and first_record['id']:
                try:
                    # 尝试按数字排序
                    return sorted(records, key=lambda x: int(x.get('id', '0')))
                except (ValueError, TypeError):
                    # 如果id字段无法转换为整数，则按字符串排序
                    return sorted(records, key=lambda x: str(x.get('id', '')))
            else:
                # 如果没有id字段，使用time字段排序
                return sorted(records, key=lambda x: str(x.get('time', '')))
            
        except Exception:
            # 如果排序失败，返回原始列表
            return records
    
    def create_merged_info(self, info1, info2):
        """
        创建合并后的info字段
        
        Args:
            info1 (dict): 第一个文件的info字段
            info2 (dict): 第二个文件的info字段
            
        Returns:
            dict: 合并后的info字段
        """
        try:
            # 基于第一个文件的info创建合并后的info
            merged_info = info1.copy() if isinstance(info1, dict) else {}
            
            # 确保必需字段存在
            if "uid" not in merged_info and isinstance(info2, dict) and "uid" in info2:
                merged_info["uid"] = info2["uid"]
            
            if "lang" not in merged_info and isinstance(info2, dict) and "lang" in info2:
                merged_info["lang"] = info2["lang"]
            
            # 设置导出应用信息
            merged_info["export_app"] = "yunzai-uigf-splitter"
            merged_info["export_app_version"] = "v1.1"
            
            # 设置格式版本信息
            if self.game_type == GameConfig.GENSHIN_IMPACT:
                merged_info["uigf_version"] = "v3.0"
            elif self.game_type == GameConfig.HONKAI_STAR_RAIL:
                merged_info["srgf_version"] = "v1.0"
            
            # 更新导出时间为当前时间
            from datetime import datetime
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            merged_info["export_time"] = current_time
            
            return merged_info
            
        except Exception:
            # 如果创建合并info失败，返回基本的info结构
            basic_info = {
                "uid": "",
                "lang": "zh-cn",
                "export_app": "yunzai-uigf-splitter",
                "export_app_version": "v1.1",
                "export_time": ""
            }
            
            # 设置格式版本
            if self.game_type == GameConfig.GENSHIN_IMPACT:
                basic_info["uigf_version"] = "v3.0"
            elif self.game_type == GameConfig.HONKAI_STAR_RAIL:
                basic_info["srgf_version"] = "v1.0"
            
            # 尝试从原始info中提取基本信息
            if isinstance(info1, dict):
                basic_info["uid"] = info1.get("uid", "")
                basic_info["lang"] = info1.get("lang", "zh-cn")
            elif isinstance(info2, dict):
                basic_info["uid"] = info2.get("uid", "")
                basic_info["lang"] = info2.get("lang", "zh-cn")
            
            # 设置当前时间
            try:
                from datetime import datetime
                basic_info["export_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                basic_info["export_time"] = ""
            
            return basic_info
    
    def merge_files(self, file1_path, file2_path, output_dir, convert_after_merge=False, progress_callback=None):
        """
        合并两个文件的完整流程
        
        Args:
            file1_path (str): 第一个文件路径
            file2_path (str): 第二个文件路径
            output_dir (str): 输出目录路径
            convert_after_merge (bool): 是否在合并后进行转换
            progress_callback (callable): 进度回调函数，接收(current, total, message)参数
            
        Returns:
            tuple: (success, error_message, result_info)
                   success (bool): 是否成功
                   error_message (str): 错误信息，如果成功则为None
                   result_info (dict): 结果信息，包含统计数据和文件路径
        """
        try:
            # 步骤1: 验证文件可合并性
            if progress_callback:
                progress_callback(10, 100, "验证文件格式和UID...")
            
            is_valid, error_msg, uid, error_details = self.validate_merge_files(file1_path, file2_path)
            if not is_valid:
                return False, error_msg, None
            
            # 步骤2: 确保输出目录存在
            if progress_callback:
                progress_callback(20, 100, "创建输出目录...")
            
            success, error_msg = create_output_directory(output_dir)
            if not success:
                return False, error_msg, None
            
            # 步骤3: 加载文件数据
            if progress_callback:
                progress_callback(30, 100, "加载文件数据...")
            
            try:
                with open(file1_path, 'r', encoding='utf-8') as f:
                    data1 = json.load(f)
                
                with open(file2_path, 'r', encoding='utf-8') as f:
                    data2 = json.load(f)
            except Exception as e:
                return False, f"加载文件数据时发生错误: {str(e)}", None
            
            # 步骤4: 合并记录
            if progress_callback:
                progress_callback(50, 100, "合并记录数据...")
            
            records1 = data1.get("list", [])
            records2 = data2.get("list", [])
            
            merged_records, merge_stats = self.merge_records(records1, records2)
            
            if "error" in merge_stats:
                return False, f"合并记录时发生错误: {merge_stats['error']}", None
            
            # 步骤5: 排序记录
            if progress_callback:
                progress_callback(60, 100, "排序合并后的记录...")
            
            sorted_records = self.sort_records_by_id(merged_records)
            
            # 步骤6: 创建合并后的info字段
            if progress_callback:
                progress_callback(70, 100, "创建合并文件信息...")
            
            info1 = data1.get("info", {})
            info2 = data2.get("info", {})
            merged_info = self.create_merged_info(info1, info2)
            
            # 步骤7: 构建合并后的数据结构
            merged_data = {
                "info": merged_info,
                "list": sorted_records
            }
            
            # 步骤8: 保存合并后的文件
            if progress_callback:
                progress_callback(80, 100, "保存合并后的文件...")
            
            # 生成合并文件名
            merged_filename = f"merged_{uid}.json"
            merged_file_path = os.path.join(output_dir, merged_filename)
            
            try:
                with open(merged_file_path, 'w', encoding='utf-8') as f:
                    json.dump(merged_data, f, ensure_ascii=False, indent=2, separators=(',', ': '))
            except Exception as e:
                return False, f"保存合并文件时发生错误: {str(e)}", None
            
            # 验证文件是否成功保存
            if not os.path.exists(merged_file_path):
                return False, f"合并文件保存失败: {merged_file_path}", None
            
            # 准备结果信息
            result_info = {
                "merged_file": merged_file_path,
                "merged_filename": merged_filename,
                "uid": uid,
                "merge_stats": merge_stats,
                "converted_files": []
            }
            
            # 步骤9: 如果需要，进行合并后转换
            if convert_after_merge:
                if progress_callback:
                    progress_callback(90, 100, "执行合并后转换...")
                
                # 导入FileProcessor进行转换
                from file_processor import FileProcessor
                
                processor = FileProcessor(self.game_type)
                convert_success, convert_error, convert_stats = processor.process_records(
                    merged_data, output_dir, progress_callback
                )
                
                if not convert_success:
                    # 转换失败，但合并成功，返回部分成功的结果
                    result_info["convert_error"] = convert_error
                else:
                    # 转换成功，添加转换统计信息
                    result_info["convert_stats"] = convert_stats
                    
                    # 列出转换后的文件
                    if convert_stats and "gacha_types" in convert_stats:
                        converted_files = []
                        for gacha_type in convert_stats["gacha_types"]:
                            converted_file = os.path.join(output_dir, f"{gacha_type}.json")
                            if os.path.exists(converted_file):
                                converted_files.append(f"{gacha_type}.json")
                        result_info["converted_files"] = converted_files
            
            # 步骤10: 完成
            if progress_callback:
                progress_callback(100, 100, "合并完成")
            
            return True, None, result_info
            
        except Exception as e:
            return False, f"合并文件时发生未知错误: {str(e)}", None
    
    def _format_uid_mismatch_error(self, uid1, uid2, file1_path, file2_path):
        """
        格式化UID不匹配的详细错误信息
        
        Args:
            uid1 (str): 第一个文件的UID
            uid2 (str): 第二个文件的UID
            file1_path (str): 第一个文件路径
            file2_path (str): 第二个文件路径
            
        Returns:
            str: 详细的错误信息
        """
        error_msg = f"两个文件的UID不匹配，无法合并:\n\n"
        error_msg += f"文件1: {os.path.basename(file1_path)}\n"
        error_msg += f"  UID: {uid1}\n\n"
        error_msg += f"文件2: {os.path.basename(file2_path)}\n"
        error_msg += f"  UID: {uid2}\n\n"
        error_msg += "解决方案:\n"
        error_msg += "• 确认两个文件都属于同一个游戏账号\n"
        error_msg += "• 检查文件是否来自同一个数据源\n"
        error_msg += "• 如果确实是不同账号的数据，请分别处理\n"
        error_msg += "• 如果UID显示错误，请检查文件格式是否正确"
        
        return error_msg
    
    def _check_game_type_compatibility(self, data1, data2):
        """
        检查两个文件的游戏类型兼容性
        
        Args:
            data1 (dict): 第一个文件的数据
            data2 (dict): 第二个文件的数据
            
        Returns:
            tuple: (is_compatible, error_message)
        """
        try:
            # 完全移除对SRGF/UIGF版本字段的检测，允许更灵活的合并
            # 不再检查版本字段，只基于用户选择的游戏类型进行gacha_type验证
            
            records1 = data1.get("list", [])
            records2 = data2.get("list", [])
            
            invalid_gacha_types = []
            
            for record in records1 + records2:
                if isinstance(record, dict) and "gacha_type" in record:
                    gacha_type = str(record["gacha_type"])
                    if gacha_type not in self.gacha_types:
                        if gacha_type not in invalid_gacha_types:
                            invalid_gacha_types.append(gacha_type)
            
            if invalid_gacha_types:
                game_name = "原神" if self.game_type == GameConfig.GENSHIN_IMPACT else "崩坏星穹铁道"
                return False, f"发现不兼容的gacha_type: {', '.join(invalid_gacha_types)}，不属于{game_name}的有效类型"
            
            return True, None
            
        except Exception as e:
            return False, f"检查游戏类型兼容性时发生错误: {str(e)}"
    
    def _check_record_quality(self, records1, records2):
        """
        检查记录质量问题
        
        Args:
            records1 (list): 第一个文件的记录列表
            records2 (list): 第二个文件的记录列表
            
        Returns:
            list: 质量问题列表
        """
        quality_issues = []
        
        try:
            # 检查记录完整性
            total_records = len(records1) + len(records2)
            invalid_records = 0
            missing_id_records = 0
            missing_time_records = 0
            
            for records, file_name in [(records1, "文件1"), (records2, "文件2")]:
                for i, record in enumerate(records):
                    if not isinstance(record, dict):
                        invalid_records += 1
                        continue
                    
                    # 检查关键字段
                    if not record.get("id"):
                        missing_id_records += 1
                    
                    if not record.get("time"):
                        missing_time_records += 1
            
            # 记录质量问题
            if invalid_records > 0:
                quality_issues.append(f"发现{invalid_records}条无效记录（非对象格式）")
            
            if missing_id_records > 0:
                quality_issues.append(f"发现{missing_id_records}条记录缺少ID字段")
            
            if missing_time_records > 0:
                quality_issues.append(f"发现{missing_time_records}条记录缺少时间字段")
            
            # 检查记录时间范围
            all_times = []
            for records in [records1, records2]:
                for record in records:
                    if isinstance(record, dict) and record.get("time"):
                        all_times.append(record["time"])
            
            if all_times:
                try:
                    from datetime import datetime
                    parsed_times = []
                    for time_str in all_times[:100]:  # 只检查前100条记录的时间
                        try:
                            parsed_time = datetime.strptime(str(time_str), "%Y-%m-%d %H:%M:%S")
                            parsed_times.append(parsed_time)
                        except ValueError:
                            continue
                    
                    if parsed_times:
                        time_span = max(parsed_times) - min(parsed_times)
                        if time_span.days > 365 * 3:  # 超过3年
                            quality_issues.append(f"记录时间跨度较大（{time_span.days}天），请确认数据正确性")
                        
                except Exception:
                    pass
            
            # 检查重复记录比例
            if records1 and records2:
                ids1 = set()
                ids2 = set()
                
                for record in records1:
                    if isinstance(record, dict) and record.get("id"):
                        ids1.add(str(record["id"]))
                
                for record in records2:
                    if isinstance(record, dict) and record.get("id"):
                        ids2.add(str(record["id"]))
                
                common_ids = ids1.intersection(ids2)
                if common_ids:
                    overlap_ratio = len(common_ids) / max(len(ids1), len(ids2)) * 100
                    if overlap_ratio > 80:
                        quality_issues.append(f"两个文件重复记录比例较高（{overlap_ratio:.1f}%），请确认是否需要合并")
            
        except Exception as e:
            quality_issues.append(f"质量检查过程中发生错误: {str(e)}")
        
        return quality_issues