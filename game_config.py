#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UIGF/SRGF 抽卡记录分离工具 - 游戏配置模块
提供原神和崩坏星穹铁道的抽卡类型配置和相关工具方法

by: 马乞
GitHub: https://github.com/maqibg/yunzai-uigf-splitte
"""

# 游戏配置字典
GAME_CONFIGS = {
    "genshin": {
        "gacha_types": ["100", "200", "301", "400", "302", "500"],
        "merge_mapping": {"400": "301"},
        "format_name": "UIGF",
        "version_field": "uigf_version"
    },
    "starrail": {
        "gacha_types": ["1", "2", "11", "12", "21"],
        "merge_mapping": {},
        "format_name": "SRGF",
        "version_field": "srgf_version"
    }
}


class GameConfig:
    """游戏配置类，包含游戏类型常量和配置管理方法"""
    
    # 游戏类型常量
    GENSHIN_IMPACT = "genshin"
    HONKAI_STAR_RAIL = "starrail"
    
    @staticmethod
    def get_gacha_types(game_type):
        """
        获取指定游戏类型对应的gacha_type列表
        
        Args:
            game_type (str): 游戏类型 ("genshin" 或 "starrail")
            
        Returns:
            list: gacha_type列表，如果游戏类型无效则返回空列表
        """
        if game_type in GAME_CONFIGS:
            return GAME_CONFIGS[game_type]["gacha_types"]
        return []
    
    @staticmethod
    def get_file_format_info(game_type):
        """
        获取指定游戏类型的文件格式信息
        
        Args:
            game_type (str): 游戏类型 ("genshin" 或 "starrail")
            
        Returns:
            dict: 包含format_name和version_field的字典，如果游戏类型无效则返回None
        """
        if game_type in GAME_CONFIGS:
            config = GAME_CONFIGS[game_type]
            return {
                "format_name": config["format_name"],
                "version_field": config["version_field"]
            }
        return None
    
    @staticmethod
    def should_merge_gacha_type(game_type, gacha_type):
        """
        判断指定的gacha_type是否需要合并到其他类型
        
        Args:
            game_type (str): 游戏类型 ("genshin" 或 "starrail")
            gacha_type (str): 抽卡类型
            
        Returns:
            str: 如果需要合并，返回目标gacha_type；否则返回原gacha_type
        """
        if game_type in GAME_CONFIGS:
            merge_mapping = GAME_CONFIGS[game_type]["merge_mapping"]
            return merge_mapping.get(gacha_type, gacha_type)
        return gacha_type