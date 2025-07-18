import os
import shutil
import pandas as pd

def filter_abstract_by_keyword(input_csv, keyword, output_csv):
    """
    从 input_csv 中筛选 abstract 含 keyword 的行，并保存为 output_csv。
    """
    df = pd.read_csv(input_csv, encoding='utf-8')
    filtered_df = df[df['abstract'].str.contains(keyword, case=False, na=False)]
    filtered_df.to_csv(output_csv, index=False)
    print(f"[INFO] 已筛选出 {len(filtered_df)} 行，保存为 '{output_csv}'")
    return filtered_df

def copy_selected_pdfs(filtered_df, source_dir, target_dir):
    """
    根据 filtered_df 中的 'no' 列，从 source_dir 拷贝匹配的 PDF 文件到 target_dir。
    """
    os.makedirs(target_dir, exist_ok=True)

    no_list = filtered_df['no'].astype(str).tolist()
    copied = 0
    missing = []

    for no in no_list:
        matched_files = [f for f in os.listdir(source_dir) if f.startswith(no + "_") and f.endswith(".pdf")]

        if matched_files:
            for file in matched_files:
                src = os.path.join(source_dir, file)
                dst = os.path.join(target_dir, file)
                shutil.copyfile(src, dst)
                copied += 1
        else:
            missing.append(no)

    print(f"[INFO] 成功复制 {copied} 个 PDF 文件到 '{target_dir}'")
    if missing:
        print(f"[WARNING] 有 {len(missing)} 个编号未找到匹配的 PDF，例如：{missing[:5]}")

def main():
    input_csv = 'paper_result_no_filter.csv'
    output_csv = 'filtered_papers.csv'
    keyword = 'empirical stud'
    source_dir = 'downloaded_pdfs'
    target_dir = 'selected_pdfs'

    # 步骤 1：过滤含关键词的行并保存
    filtered_df = filter_abstract_by_keyword(input_csv, keyword, output_csv)

    # 步骤 2：根据 no 字段复制 PDF
    copy_selected_pdfs(filtered_df, source_dir, target_dir)

if __name__ == '__main__':
    main()
