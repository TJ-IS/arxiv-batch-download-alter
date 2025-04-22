import pandas as pd
import os
from pathlib import Path
import requests
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import re
from tqdm import tqdm  # 引入进度条
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
            # print(f"Downloaded: {file_path}")
        else:
            output_queue.put(f"No PDF, skipping: 【{title}】 -> {pdf_url}")
    except Exception as e:
        output_queue.put(f"Failed to download {title} {pdf_url}: {e}")


def papers_file_core(path_of_csv, proxies_port=None, max_workers=3):
    # 读取CSV文件
    df = pd.read_csv(path_of_csv)

    # 提取年份
    df['year'] = pd.to_datetime(df['submission_date']).dt.year

    # 创建以年份命名的文件夹
    base_dir = "papers_by_year"
    os.makedirs(base_dir, exist_ok=True)

    year_folders = {}
    for year in df['year'].unique():
        year_folder = os.path.join(base_dir, str(year))
        os.makedirs(year_folder, exist_ok=True)
        year_folders[year] = year_folder

    # 设置本地代理
    if proxies_port is not None:
        proxies = {
            "http": f"http://127.0.0.1:{proxies_port}",
            "https": f"http://127.0.0.1:{proxies_port}"
        }
    else:
        proxies = None

    # 创建一个线程安全的队列
    output_queue = queue.Queue()

    # 使用线程池下载并添加进度条
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 使用 executor 添加任务到 futures
        futures = [executor.submit(download_paper, row, year_folders, proxies, output_queue) for _, row in df.iterrows()]
        # 添加进度条，便于检测下载进度
        for future in tqdm(futures, desc="Downloading papers", mininterval=0.1, maxinterval=60, ncols=150, total=len(futures)):
            future.result()  # 等待所有任务完成

    # 在所有任务完成后，统一输出文本
    while not output_queue.empty():
        print(output_queue.get())

    print("Done!")


if __name__ == '__main__':
    papers_file_core(path_of_csv="paper_result.csv", proxies_port=10808, max_workers=3)
