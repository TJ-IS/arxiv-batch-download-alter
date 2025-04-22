import pandas as pd
import os
from pathlib import Path
import requests
from datetime import datetime
import re


def papers_file_core(path_of_csv, proxies_port=None):
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

    # 清理非法文件名字符
    def sanitize_filename(title):
        return re.sub(r'[\\/*?:"<>|]', "", title)

    # 设置本地代理
    if proxies_port is not None:
        proxies = {
            "http": f"http://127.0.0.1:{proxies_port}",
            "https": f"http://127.0.0.1:{proxies_port}"
        }

    # 下载PDF并保存到对应文件夹
    for _, row in df.iterrows():
        title = sanitize_filename(row['title'])
        year = row['year']
        pdf_url = row['pdf_link']
        folder_path = year_folders[year]
        file_path = Path(folder_path) / f"{title}.pdf"

        try:
            if pdf_url != "No PDF link found":
                if not proxies:
                    response = requests.get(pdf_url)
                else:
                    response = requests.get(pdf_url, proxies=proxies)
                response.raise_for_status()
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                print(f"Downloaded: {file_path}")
            else:
                print(f"No PDF, skipping: {title} {pdf_url}")
        except Exception as e:
            print(f"Failed to download {title} {pdf_url}: {e}")

    print("Done!")


if __name__ == '__main__':
    papers_file_core(path_of_csv="paper_result.csv", proxies_port=10808)
