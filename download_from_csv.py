import pandas as pd
import os
from pathlib import Path
import requests
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import re
from tqdm import tqdm
import queue
import time # Import time module for delays


# 清理非法文件名字符
def sanitize_filename(title):
    """
    Cleans illegal characters from a string to be used as a filename,
    replacing them with underscores.
    """
    # Replace all illegal characters with underscores
    cleaned_title = re.sub(r'[\\/*?:"<>|]', "_", title)
    # Remove leading/trailing spaces from the filename
    return cleaned_title.strip()


# 下载PDF并保存到指定文件夹
def download_paper(row, download_dir, proxies, output_queue):
    """
    Downloads a single PDF file and saves it to the specified directory.
    The file is named in the format: no_year_title.pdf
    """
    title = sanitize_filename(row['title'])
    # Ensure year exists, if not, use 'Unknown'
    year = row['year'] if 'year' in row and pd.notna(row['year']) else 'Unknown'
    pdf_url = row['pdf_link']
    
    # Get 'no' value from the row. If not present or NaN, default to 'UnknownNo'.
    paper_no = row['no'] if 'no' in row and pd.notna(row['no']) else 'UnknownNo'
    # Convert paper_no to string to ensure it can be concatenated
    paper_no_str = str(paper_no) 

    # Construct the full file path: no_year_title.pdf
    file_path = Path(download_dir) / f"{paper_no_str}_{year}_{title}.pdf"

    try:
        if pd.isna(pdf_url) or pdf_url == "No PDF link found":
            # If no PDF link, log and skip
            output_queue.put(f"无PDF链接，跳过下载: 《{row['title']}》")
            return

        # Check if the file already exists, skip download if it does
        if file_path.exists():
            output_queue.put(f"文件已存在，跳过下载: 《{row['title']}》 -> {file_path}")
            return

        # Send HTTP GET request to download the PDF
        response = requests.get(pdf_url, proxies=proxies, timeout=30) # Added timeout setting
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)

        # Write the downloaded content to the file
        with open(file_path, 'wb') as f:
            f.write(response.content)
        output_queue.put(f"成功下载: 《{row['title']}》 -> {file_path}")
        
        time.sleep(3) # Add a 3-second delay after each successful download

    except requests.exceptions.RequestException as e:
        # Catch request-related exceptions (e.g., connection errors, timeouts, HTTP errors)
        output_queue.put(f"下载失败: 《{row['title']}》 -> 【{pdf_url}】: {e}")
    except Exception as e:
        # Catch other unexpected exceptions
        output_queue.put(f"处理失败: 《{row['title']}》 -> 【{pdf_url}】: {e}")


def papers_file_core(path_of_csv, proxies_port=None, max_workers=3, start_from_no=None, specific_nos_list=None): # MODIFIED: Added specific_nos_list parameter
    """
    Core function for downloading PDF papers from a CSV file.
    """
    # Set up local proxies if a proxy port is provided
    proxies = {
        "http": f"http://127.0.0.1:{proxies_port}",
        "https": f"http://127.0.0.1:{proxies_port}"
    } if proxies_port is not None else None

    try:
        # Read the CSV file
        df = pd.read_csv(path_of_csv)
    except FileNotFoundError:
        print(f"错误：找不到文件 '{path_of_csv}'。请检查文件路径。")
        return
    except Exception as e:
        print(f"读取CSV文件时发生错误: {e}")
        return

    # Ensure 'submission_date' column exists and convert to datetime format
    if 'submission_date' not in df.columns:
        print("错误：CSV文件中缺少 'submission_date' 列。")
        return
    
    # Try to convert 'submission_date' to datetime, handling possible errors
    df['submission_date'] = pd.to_datetime(df['submission_date'], errors='coerce')
    # Extract year from 'submission_date', fill NaN with 'Unknown' if conversion fails
    df['year'] = df['submission_date'].dt.year.fillna('Unknown').astype(str) 

    # Ensure 'no' column exists. If not, print a warning but continue.
    if 'no' not in df.columns:
        print("警告：CSV文件中缺少 'no' 列。文件名将使用 'UnknownNo' 作为前缀。")
        # Add a placeholder 'no' column if it doesn't exist
        df['no'] = 'UnknownNo'
    
    # MODIFIED: New filtering logic for specific_nos_list
    if specific_nos_list is not None and len(specific_nos_list) > 0:
        try:
            # Convert 'no' column to numeric for comparison, coercing errors
            df['no_numeric'] = pd.to_numeric(df['no'], errors='coerce')
            # Filter rows where 'no_numeric' is in the specific_nos_list
            df = df[df['no_numeric'].isin(specific_nos_list)].drop(columns=['no_numeric'])
            print(f"将只下载 'no' 值为 {specific_nos_list} 的PDF文件。")
        except Exception as e:
            print(f"处理 'specific_nos_list' 时发生错误: {e}. 将下载所有文件。")
    # MODIFIED: Original filtering logic for start_from_no, only applied if specific_nos_list is not used
    elif start_from_no is not None:
        try:
            # Convert 'no' column to numeric for comparison, coercing errors
            df['no_numeric'] = pd.to_numeric(df['no'], errors='coerce')
            # Filter rows where 'no_numeric' is greater than or equal to start_from_no
            # Also drop rows where 'no_numeric' became NaN due to conversion errors
            df = df[df['no_numeric'] >= start_from_no].drop(columns=['no_numeric'])
            print(f"将只下载 'no' 值大于或等于 {start_from_no} 的PDF文件。")
        except Exception as e:
            print(f"处理 'start_from_no' 时发生错误: {e}. 将下载所有文件。")


    # Ensure 'title' and 'pdf_link' columns exist
    if 'title' not in df.columns or 'pdf_link' not in df.columns:
        print("错误：CSV文件中缺少 'title' 或 'pdf_link' 列。")
        return

    # Define a single download directory for all PDFs
    download_base_dir = "downloaded_pdfs"
    os.makedirs(download_base_dir, exist_ok=True) # Create the directory if it doesn't exist

    print(f"将所有PDF下载到: {download_base_dir}")
    # MODIFIED: Update total count after filtering
    print(f"总计找到 {len(df)} 篇论文进行处理。")

    # Create a thread-safe output queue to collect download logs
    output_queue = queue.Queue()

    # Use a thread pool for concurrent downloads
    # Filter out rows without title or PDF link to avoid unnecessary processing
    papers_to_download = df[df['title'].notna() & df['pdf_link'].notna()]

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit download tasks to the thread pool
        futures = [executor.submit(download_paper, row, download_base_dir, proxies, output_queue) 
                   for _, row in papers_to_download.iterrows()]
        
        # Use tqdm to display download progress
        for future in tqdm(futures, desc="下载论文中", mininterval=0.1, ncols=100, total=len(futures)):
            future.result() # Ensure all tasks complete and catch potential exceptions

    # After downloads, print all log messages
    print("\n--- 下载结果日志 ---")
    while not output_queue.empty():
        print(output_queue.get())

    print("\n所有PDF下载任务已完成！")


if __name__ == '__main__':
    # Example usage: Please replace 'paper_result.csv' with your CSV file path
    # The proxies_port parameter can be set to your proxy port, e.g., 7890
    # Example usage for start_from_no. Set to None to download all.
    # MODIFIED: Example usage for specific_nos_list.
    # To download specific 'no' values (e.g., 21 and 34):
    # papers_file_core(path_of_csv="paper_result.csv", proxies_port=None, max_workers=5, specific_nos_list=[21, 34])
    # To download from a specific 'no' onwards (e.g., from 10 onwards):
    # papers_file_core(path_of_csv="paper_result.csv", proxies_port=None, max_workers=5, start_from_no=10)
    # To download all (default):
    papers_file_core(path_of_csv="paper_result_no.csv", proxies_port=None, max_workers=3, start_from_no=None, specific_nos_list=[355, 390, 413, 977, 1132, 1978, 2792])
