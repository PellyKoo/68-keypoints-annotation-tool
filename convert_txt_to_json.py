#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TXT标注转JSON标注工具
将txt格式的关键点标注转换为工具可用的JSON格式
"""

import sys
import json
import os
from pathlib import Path


def convert_txt_to_json(txt_file, image_file):
    """
    将txt标注文件转换为JSON格式

    Args:
        txt_file: txt标注文件路径
        image_file: 对应的图片文件路径

    Returns:
        bool: 转换是否成功
    """
    try:
        # 读取txt文件
        with open(txt_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()

        # 解析坐标（假设是空格分隔的x1 y1 x2 y2 ... x68 y68）
        coords = content.split()
        coords = [float(c) for c in coords]

        # 检查坐标数量
        if len(coords) != 136:  # 68个点，每个点2个坐标
            print(f"  ✗ 坐标数量不正确: {len(coords)}，期望136 (68个点x2)")
            return False

        # 构建关键点列表
        keypoints = []
        for i in range(68):
            x = coords[i * 2]
            y = coords[i * 2 + 1]
            keypoints.append({
                'id': i + 1,
                'x': round(x, 6),
                'y': round(y, 6)
            })

        # 构建JSON数据
        data = {
            'image_name': image_file.name,
            'keypoints': keypoints
        }

        # 保存JSON文件
        json_file = image_file.with_suffix('.json')
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"  ✓ 成功转换: {json_file.name}")
        return True

    except Exception as e:
        print(f"  ✗ 转换失败: {e}")
        return False


def batch_convert(directory):
    """
    批量转换目录中的所有txt标注文件

    Args:
        directory: 包含图片和txt文件的目录
    """
    import io
    # 设置输出编码为 UTF-8
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    directory = Path(directory)

    if not directory.exists():
        print(f"目录不存在: {directory}")
        return

    # 查找所有txt文件
    txt_files = list(directory.glob('*.txt'))

    if not txt_files:
        print(f"目录中没有找到txt文件: {directory}")
        return

    print(f"找到 {len(txt_files)} 个txt标注文件")
    print("=" * 60)

    success_count = 0
    fail_count = 0

    for txt_file in txt_files:
        # 查找对应的图片文件
        image_file = None
        for ext in ['.jpg', '.jpeg', '.png', '.bmp', '.JPG', '.JPEG', '.PNG', '.BMP']:
            img_path = txt_file.with_suffix(ext)
            if img_path.exists():
                image_file = img_path
                break

        if not image_file:
            print(f"跳过 {txt_file.name}: 找不到对应的图片文件")
            fail_count += 1
            continue

        print(f"\n处理: {txt_file.name} -> {image_file.name}")

        if convert_txt_to_json(txt_file, image_file):
            success_count += 1
        else:
            fail_count += 1

    # 总结
    print("\n" + "=" * 60)
    print("转换完成！")
    print(f"成功: {success_count} 个")
    print(f"失败: {fail_count} 个")


def main():
    """主函数"""
    print("=" * 60)
    print("TXT标注转JSON标注工具")
    print("=" * 60)
    print()

    if len(sys.argv) < 2:
        print("用法:")
        print("  python convert_txt_to_json.py <目录路径>")
        print()
        print("示例:")
        print("  python convert_txt_to_json.py ./demo_jpg")
        print()
        print("说明:")
        print("  - 将目录中所有txt标注文件转换为JSON格式")
        print("  - txt格式: x1 y1 x2 y2 ... x68 y68（空格分隔，比例坐标）")
        print("  - JSON格式: 工具可用的标准格式")
        print("  - 自动查找同名的图片文件")
        print()
        return

    directory = sys.argv[1]
    batch_convert(directory)


if __name__ == '__main__':
    main()
