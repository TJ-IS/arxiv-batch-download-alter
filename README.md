### arxiv网站关键词论文下载脚本
改编自https://github.com/HuiXiaHeYu/arxiv-batch-download.

增加了基于编号续传和对comment进行筛选.

> arxiv官网：https://arxiv.org/search/

**参数**
- keywords: 关键词【可修改】
- searchtype: 搜索模式`[all/title/author/abstract/comments/journal_ref/acm_class/msc_class/report_num/paper_id/doi/orcid/license/author_id/help/full_text]`[可修改]
- page_size: 爬取速率`[25/50/100/200]`【可修改】
- path_of_csv: 总论文信息csv文件路径【默认不需要修改】
- proxies_port: 使用代理端口，不填则使用临时本地端口【网速慢可修改为对应端口】
- max_workers: 线程池中的线程数【与本地网速有关，默认为3】


## 🛠️ 安装要求

- Python 3.12 或更高版本
- [uv](https://github.com/astral-sh/uv) 包管理工具

> 
> ## On Windows.
> powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
> 

## 使用 uv 创建虚拟环境并安装依赖
```bash
uv venv .venv
uv sync
```

**arxiv使用**
```python
uv sync
```

```python
uv run __init__.py
```
核心函数：

papers_info_core，获得文献信息，包括comment

papers_file_core，支持基于编号续传，包括：输入起始编号或指定编号列表

**编号生成**

基于文献信息进行编号生成，注意文件名称

```python
uv run rename.py
```

**comment筛选**

筛选近期发表内容 (需适配年份)

```python
uv run filter.py
```

**其他功能1**

EBSCOpdf下载，指定EBSCO元数据csv文件夹，指定输出文件夹 (默认为根目录下pdfs)，配置edge访问权限 (能够访问EBSCO)即可.

指定csv文件夹时，允许子文件夹中存放csv文件

环境变量需要有msedgedriver.exe所在位置

启动时edge不能有其他页面

```python
uv run EBSCO_getpdf.py
```

**其他功能2**

INFORMSpdf下载，指定INFORMS元数据csv文件夹，指定输出文件夹 (默认为根目录下informs_pdfs)，配置edge访问权限 (能够访问INFORMS)即可.

指定csv文件夹时，允许子文件夹中存放csv文件

环境变量需要有msedgedriver.exe所在位置

启动时edge不能有其他页面

```python
uv run INFORMS_getpdf.py
```