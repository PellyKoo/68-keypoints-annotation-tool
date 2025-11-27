#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查依赖项是否正确安装
"""

import sys

def check_dependencies():
    """检查所有依赖项"""
    import sys
    import io

    # 设置输出编码为 UTF-8
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("=" * 60)
    print("检查 68 关键点标注工具 依赖项")
    print("=" * 60)
    print()

    all_ok = True

    # 检查 Python 版本
    print("1. 检查 Python 版本...")
    python_version = sys.version_info
    print(f"   当前版本: Python {python_version.major}.{python_version.minor}.{python_version.micro}")

    if python_version.major >= 3 and python_version.minor >= 7:
        print("   ✓ Python 版本符合要求 (>= 3.7)")
    else:
        print("   ✗ Python 版本过低，需要 Python 3.7 或更高版本")
        all_ok = False
    print()

    # 检查 PyQt5
    print("2. 检查 PyQt5...")
    try:
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import Qt, QT_VERSION_STR
        from PyQt5.QtGui import QPixmap
        print(f"   当前版本: PyQt5 {QT_VERSION_STR}")
        print("   ✓ PyQt5 安装正确")
    except ImportError as e:
        print(f"   ✗ PyQt5 未安装或安装不完整")
        print(f"   错误信息: {e}")
        print("   请运行: pip install PyQt5")
        all_ok = False
    print()

    # 检查标准库
    print("3. 检查标准库...")
    try:
        import json
        import os
        from pathlib import Path
        print("   ✓ 标准库完整")
    except ImportError as e:
        print(f"   ✗ 标准库缺失: {e}")
        all_ok = False
    print()

    # 检查文件结构
    print("4. 检查项目文件...")
    from pathlib import Path

    required_files = [
        "keypoint_annotation_tool.py",
    ]

    current_dir = Path(__file__).parent
    missing_files = []

    for filename in required_files:
        filepath = current_dir / filename
        if filepath.exists():
            print(f"   ✓ {filename}")
        else:
            print(f"   ✗ {filename} 缺失")
            missing_files.append(filename)

    if missing_files:
        all_ok = False
    print()

    # 检查标准图目录
    print("5. 检查标准图目录...")
    std_pic_dir = current_dir / "std_pic"
    if std_pic_dir.exists():
        print(f"   ✓ std_pic 目录存在")

        # 检查是否有标准图
        std_image = std_pic_dir / "facial_landmarks_68markup.jpg"
        if std_image.exists():
            print(f"   ✓ 找到标准参考图")
        else:
            print(f"   ! 未找到标准参考图 (可选)")
            print(f"     请将标准图放在: {std_image}")
    else:
        print(f"   ! std_pic 目录不存在 (可选)")
        print(f"     程序会自动创建")
    print()

    # 总结
    print("=" * 60)
    if all_ok:
        print("✓ 所有检查通过！可以运行程序了。")
        print()
        print("运行方法:")
        print("  python keypoint_annotation_tool.py")
    else:
        print("✗ 发现问题，请先解决上述错误。")
        print()
        print("常见解决方法:")
        print("  1. 安装 PyQt5: pip install PyQt5")
        print("  2. 升级 Python: 下载最新版本 Python 3.9+")
        print("  3. 检查文件完整性")
    print("=" * 60)

    return all_ok


if __name__ == '__main__':
    success = check_dependencies()
    sys.exit(0 if success else 1)
