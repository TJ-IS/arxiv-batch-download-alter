import pandas as pd
import os
from pathlib import Path
import requests
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import re
from tqdm import tqdm
import queue


# 清理非法文件名字符
def sanitize_filename(title):
    return re.sub(r'[\\/*?:"<>|]', "", title)


# 下载PDF并保存到对应文件夹
def download_paper(row, year_folders, proxies, output_queue):
    title = sanitize_filename(row['title'])
    year = row['year']
    pdf_url = row['pdf_link']
    folder_path = year_folders[year]
    file_path = Path(folder_path) / f"{title}.pdf"

    try:
        if pdf_url != "No PDF link found":
            response = requests.get(pdf_url, proxies=proxies)
            response.raise_for_status()
            with open(file_path, 'wb') as f:
                f.write(response.content)
        else:
            output_queue.put(f"No PDF, skipping: 【{title}】 -> {pdf_url}")
    except Exception as e:
        output_queue.put(f"Failed to download {title} {pdf_url}: {e}")


def papers_file_core(path_of_csv, proxies_port=None, max_workers=3):
    # 设置本地代理
    proxies = {
        "http": f"http://127.0.0.1:{proxies_port}",
        "https": f"http://127.0.0.1:{proxies_port}"
    } if proxies_port is not None else None

    # 读取CSV文件
    df = pd.read_csv(path_of_csv)
    df['year'] = pd.to_datetime(df['submission_date']).dt.year

    # 输出所有年份及论文数
    year_counts = df['year'].value_counts().sort_index()
    print("可选年份及对应论文数量：")
    for year, count in year_counts.items():
        print(f" - {year}: {count} 篇")

    # 用户选择年份
    year_input = input("\n请输入要下载的年份（多个年份用逗号分隔，例如 2022,2023）：")
    selected_years = [int(y.strip()) for y in year_input.split(",") if y.strip().isdigit()]
    df = df[df['year'].isin(selected_years)]

    if df.empty:
        print("没有符合条件的论文，程序结束。")
        return

    # 创建以年份命名的文件夹
    base_dir = "papers_by_year"
    os.makedirs(base_dir, exist_ok=True)
    year_folders = {}
    for year in df['year'].unique():
        year_folder = os.path.join(base_dir, str(year))
        os.makedirs(year_folder, exist_ok=True)
        year_folders[year] = year_folder

    # 创建线程安全输出队列
    output_queue = queue.Queue()

    # 并发下载
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(download_paper, row, year_folders, proxies, output_queue) for _, row in df.iterrows()]
        for future in tqdm(futures, desc="Downloading papers", mininterval=0.1, ncols=150, total=len(futures)):
            future.result()

    # 下载后统一输出日志
    while not output_queue.empty():
        print(output_queue.get())

    print("Done!")


if __name__ == '__main__':
    papers_file_core(path_of_csv="paper_result.csv", proxies_port=10808, max_workers=3)
