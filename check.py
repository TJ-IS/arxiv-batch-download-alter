import os
import re

def check_file_sequence_optimized(directory_path):
    """
    检查指定目录下 'no_year_title.pdf' 格式的文件名中 'no' 字段的连续性。
    优化版：直接使用 split('_') 提取 'no' 字段。

    Args:
        directory_path (str): 要检查的目录路径。
    """
    file_numbers = set()
    # 匹配以数字开头，后跟下划线，以 .pdf 结尾的文件名
    # 例如：123_2023_title.pdf
    pattern = re.compile(r'^\d+_.*\.pdf$', re.IGNORECASE)

    try:
        for filename in os.listdir(directory_path):
            if pattern.match(filename):
                try:
                    # 直接获取第一个下划线前的部分并转换为整数
                    file_number = int(filename.split('_')[0])
                    file_numbers.add(file_number)
                except ValueError:
                    print(f"警告：文件 '{filename}' 的文件名开头不是有效的数字，已跳过。")
    except FileNotFoundError:
        print(f"错误：目录 '{directory_path}' 不存在。")
        return

    if not file_numbers:
        print(f"在目录 '{directory_path}' 中未找到符合 'no_year_title.pdf' 格式的文件。")
        return

    min_no = min(file_numbers)
    max_no = max(file_numbers)

    print(f"找到的 'no' 字段范围从 {min_no} 到 {max_no}。")

    missing_numbers = []
    for i in range(min_no, max_no + 1):
        if i not in file_numbers:
            missing_numbers.append(i)

    if missing_numbers:
        print("\n以下 'no' 字段不连贯或缺失：")
        for num in missing_numbers:
            print(f"- {num}")
        return missing_numbers
    else:
        print("\n所有 'no' 字段都是连贯的！")

# --- 使用方法 ---
if __name__ == "__main__":
    # 将 'your_directory_path' 替换为你的文件所在的实际目录
    # 例如: r"C:\Users\YourUser\Documents\MyPDFs" 或者 "/home/youruser/pdfs"
    target_directory = ".\downloaded_pdfs" 
    missing_numbers = check_file_sequence_optimized(target_directory)
    print(missing_numbers)