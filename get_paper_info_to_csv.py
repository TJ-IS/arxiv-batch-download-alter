"""
爬取论文信息
"""
from datetime import datetime

from lxml import html
import requests
import re
import math
import csv
from bs4 import BeautifulSoup
import time


def get_total_results(url, headers, params):
    """一共多少篇文章"""
    response = requests.get(url, headers=headers, params=params)
    tree = html.fromstring(response.content)
    result_string = ''.join(tree.xpath('//*[@id="main-container"]/div[1]/div[1]/h1/text()')).strip()
    match = re.search(r'of ([\d,]+) results', result_string)
    if match:
        total_results = int(match.group(1).replace(',', ''))
        return total_results
    else:
        print("没有找到匹配的数字。")
        return 0


def get_paper_info(url, headers, params):
    """根据URL爬取一页的论文信息"""
    response = requests.get(url, headers=headers, params=params)
    soup = BeautifulSoup(response.content, 'html.parser')
    papers = []

    for article in soup.find_all('li', class_='arxiv-result'):
        title = article.find('p', class_='title').text.strip()

        authors_text = article.find('p', class_='authors').text.replace('Authors:', '').strip().split(',')
        authors = [author.strip() for author in authors_text]

        abstract = article.find('span', class_='abstract-full').text.strip()

        submitted_element = article.find('p', class_='is-size-7').text.strip().split(';')[0].replace('Submitted', '').strip()
        submission_date = datetime.strptime(submitted_element, "%d %B, %Y").strftime("%Y-%m-%d")

        pdf_link_element = article.find('a', string='pdf')
        pdf_link = pdf_link_element['href'] if pdf_link_element else 'No PDF link found'

        papers.append({'title': title,
                       'authors': authors,
                       'abstract': abstract,
                       'submission_date': submission_date,
                       'pdf_link': pdf_link})

    return papers


def save_to_csv(papers, filename):
    """将所有爬取的论文信息保存到CSV文件中"""
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['title', 'authors', 'abstract', 'submission_date', 'pdf_link']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for paper in papers:
            writer.writerow(paper)


def papers_info_core(keywords, page_size):
    # 修改这里的链接
    base_url = "https://arxiv.org/search/"
    base_params = {
        "query": keywords,    # 关键词
        "searchtype": "all",
        "abstracts": "show",
        "order": "-announced_date_first",
        "size": str(page_size),
        "start": "0"
    }
    base_headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    }
    total_results = get_total_results(base_url, base_headers, base_params)
    pages = math.ceil(total_results / page_size)
    all_papers = []

    for page in range(pages):
        start = page * page_size
        print(f"Crawling page {page + 1}/{pages}, start={start}")
        base_params["start"] = start    # 将参数中的start更改
        all_papers.extend(get_paper_info(base_url, base_headers, base_params))
        time.sleep(3)  # 等待三秒以避免对服务器造成过大压力

    # 保存到CSV
    save_to_csv(all_papers, 'paper_result.csv')
    print(f"完成！总共爬取到 {len(all_papers)} 条论文信息【包含：title、authors、abstract、submission_date、pdf_link】，已保存到 paper_result.csv 文件中。")


if __name__ == '__main__':
    papers_info_core(keywords="text spotter", page_size=200)

