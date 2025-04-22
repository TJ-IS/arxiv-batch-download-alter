### arxiv网站关键词论文下载脚本
**参数**
- papers_info_core:
    - keywords: 关键词【可修改】
    - page_size: 爬取速率[25/50/100/200]【可修改】
- papers_file_core:
    - path_of_csv: 总论文信息csv文件路径【默认不需要修改】
    - proxies_port: 使用代理端口，不填则使用临时本地端口【网速慢可挂VPN后修改为对应端口】

**开始使用**
```python
python __init__.py
```

**未来**
- [ ]  加入多线程  