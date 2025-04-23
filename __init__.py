"""
@-*- coding: utf-8 -*-
@ python：python 3.8
@ 创建人员：HuiXiaHeYu
@ 创建时间：2025/4/22
"""
from get_paper_info_to_csv import papers_info_core
from download_from_csv import papers_file_core

if __name__ == '__main__':
    """
    arxiv网站关键词论文下载脚本
    args:
        keywords: 关键词【可修改】
        searchtype: 搜索模式[all/title/author/abstract/comments/journal_ref/acm_class/msc_class/report_num/paper_id/doi/orcid/license/author_id/help/full_text]
        page_size: 爬取速率[25/50/100/200]【可修改】
        path_of_csv: 总论文信息csv文件路径【默认不需要修改】
        proxies_port: 使用代理端口，不填则使用临时本地端口【网速慢可挂VPN后修改为对应端口】
        max_workers: 线程池中的线程数【与本地网速有关，默认为3】
    """
    print("你好！欢迎使用arxiv文献下载器")
    papers_info_core(keywords="scene text spotter", searchtype="abstract", page_size=200, proxies_port=10808)
    papers_file_core(path_of_csv="paper_result.csv", proxies_port=10808, max_workers=3)
