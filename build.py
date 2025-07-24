#!/usr/bin/env python3
"""
构建脚本 - 使用PyInstaller创建可执行文件
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def clean_build_dirs():
    """清理构建目录"""
    dirs_to_clean = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"清理目录: {dir_name}")
            shutil.rmtree(dir_name)
    
    # 清理.spec文件
    spec_files = [f for f in os.listdir('.') if f.endswith('.spec')]
    for spec_file in spec_files:
        print(f"删除文件: {spec_file}")
        os.remove(spec_file)

def build_executable():
    """构建可执行文件"""
    print("开始构建可执行文件...")
    
    # PyInstaller命令参数
    cmd = [
        'pyinstaller',
        '--onefile',           # 打包成单个文件
        '--windowed',          # Windows下隐藏控制台窗口
        '--name=UIGF抽卡记录分离工具',  # 可执行文件名称
        '--icon=icon.ico',     # 图标文件（如果存在）
        '--add-data=README.md;.',  # 包含README文件
        'main.py'              # 主程序文件
    ]
    
    # 如果没有图标文件，移除图标参数
    if not os.path.exists('icon.ico'):
        cmd.remove('--icon=icon.ico')
    
    try:
        # 执行PyInstaller命令
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("构建成功！")
        print(result.stdout)
        
        # 检查输出文件
        exe_path = Path('dist/UIGF抽卡记录分离工具.exe')
        if exe_path.exists():
            file_size = exe_path.stat().st_size / (1024 * 1024)  # MB
            print(f"可执行文件已生成: {exe_path}")
            print(f"文件大小: {file_size:.2f} MB")
            return True
        else:
            print("错误: 可执行文件未生成")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"构建失败: {e}")
        print(f"错误输出: {e.stderr}")
        return False

def test_executable():
    """测试可执行文件"""
    exe_path = Path('dist/UIGF抽卡记录分离工具.exe')
    if not exe_path.exists():
        print("错误: 可执行文件不存在")
        return False
    
    print("测试可执行文件...")
    try:
        # 启动程序并立即关闭（测试是否能正常启动）
        process = subprocess.Popen([str(exe_path)], 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE)
        
        # 等待一小段时间让程序启动
        import time
        time.sleep(2)
        
        # 终止进程
        process.terminate()
        process.wait(timeout=5)
        
        print("可执行文件测试通过")
        return True
        
    except Exception as e:
        print(f"可执行文件测试失败: {e}")
        return False

def create_release_package():
    """创建发布包"""
    print("创建发布包...")
    
    release_dir = Path('release')
    if release_dir.exists():
        shutil.rmtree(release_dir)
    
    release_dir.mkdir()
    
    # 复制可执行文件
    exe_path = Path('dist/UIGF抽卡记录分离工具.exe')
    if exe_path.exists():
        shutil.copy2(exe_path, release_dir)
    
    # 复制文档文件
    docs_to_copy = ['README.md', 'requirements.txt']
    for doc in docs_to_copy:
        if os.path.exists(doc):
            shutil.copy2(doc, release_dir)
    
    # 创建使用说明
    usage_text = """UIGF/SRGF 抽卡记录分离工具 - 使用说明

1. 双击 "UIGF抽卡记录分离工具.exe" 启动程序
2. 选择游戏类型（原神或崩坏：星穹铁道）
3. 选择输入的抽卡记录JSON文件
4. 选择输出目录
5. 点击"开始转换"按钮

详细说明请参考 README.md 文件。

如有问题，请查看 README.md 中的常见问题解答部分。
"""
    
    with open(release_dir / '使用说明.txt', 'w', encoding='utf-8') as f:
        f.write(usage_text)
    
    print(f"发布包已创建: {release_dir}")
    
    # 显示发布包内容
    print("发布包内容:")
    for item in release_dir.iterdir():
        if item.is_file():
            size = item.stat().st_size
            if size > 1024 * 1024:
                size_str = f"{size / (1024 * 1024):.2f} MB"
            elif size > 1024:
                size_str = f"{size / 1024:.2f} KB"
            else:
                size_str = f"{size} bytes"
            print(f"  {item.name} ({size_str})")

def main():
    """主函数"""
    print("UIGF/SRGF 抽卡记录分离工具 - 构建脚本")
    print("=" * 50)
    
    # 检查Python版本
    if sys.version_info < (3, 7):
        print("错误: 需要Python 3.7或更高版本")
        return False
    
    # 检查必需文件
    required_files = ['main.py', 'file_processor.py', 'game_config.py', 'utils.py']
    for file in required_files:
        if not os.path.exists(file):
            print(f"错误: 缺少必需文件 {file}")
            return False
    
    try:
        # 1. 清理构建目录
        clean_build_dirs()
        
        # 2. 构建可执行文件
        if not build_executable():
            return False
        
        # 3. 测试可执行文件
        if not test_executable():
            print("警告: 可执行文件测试失败，但构建已完成")
        
        # 4. 创建发布包
        create_release_package()
        
        print("\n" + "=" * 50)
        print("构建完成！")
        print("可执行文件位置: dist/UIGF抽卡记录分离工具.exe")
        print("发布包位置: release/")
        
        return True
        
    except KeyboardInterrupt:
        print("\n构建被用户中断")
        return False
    except Exception as e:
        print(f"构建过程中发生错误: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)