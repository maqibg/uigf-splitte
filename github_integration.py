#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UIGF/SRGF 抽卡记录分离工具 - GitHub集成模块
提供GitHub仓库链接跳转和相关功能

by: 马乞
GitHub: https://github.com/maqibg/yunzai-uigf-splitte
"""

import webbrowser
import tkinter.messagebox as messagebox


class GitHubIntegration:
    """GitHub集成功能类"""
    
    # 项目信息常量
    AUTHOR_NAME = "马乞"
    REPO_URL = "https://github.com/maqibg/yunzai-uigf-splitte"
    REPO_NAME = "yunzai-uigf-splitte"
    
    @staticmethod
    def open_github_repo():
        """
        打开GitHub仓库链接
        
        Returns:
            tuple: (成功状态, 消息)
        """
        try:
            # 尝试打开浏览器并跳转到GitHub仓库
            webbrowser.open(GitHubIntegration.REPO_URL)
            return True, "成功打开GitHub仓库"
            
        except Exception as e:
            # 如果打开失败，显示错误信息和手动访问选项
            error_msg = f"无法自动打开浏览器: {str(e)}"
            
            # 显示包含仓库链接的对话框供用户手动复制
            messagebox.showinfo(
                "GitHub仓库链接", 
                f"无法自动打开浏览器，请手动访问以下链接：\n\n"
                f"{GitHubIntegration.REPO_URL}\n\n"
                f"您可以复制此链接到浏览器地址栏中访问。"
            )
            
            return False, error_msg
    
    @staticmethod
    def get_author_info():
        """
        获取作者信息
        
        Returns:
            dict: 包含作者信息的字典
        """
        return {
            "name": GitHubIntegration.AUTHOR_NAME,
            "repo_url": GitHubIntegration.REPO_URL,
            "repo_name": GitHubIntegration.REPO_NAME
        }
    
    @staticmethod
    def validate_repo_url():
        """
        验证仓库URL格式是否正确
        
        Returns:
            bool: URL格式是否正确
        """
        expected_pattern = f"https://github.com/maqibg/{GitHubIntegration.REPO_NAME}"
        return GitHubIntegration.REPO_URL == expected_pattern