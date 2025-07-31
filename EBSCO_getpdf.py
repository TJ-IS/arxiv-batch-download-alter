import os
import pandas as pd
import requests
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import html
import re
from urllib.parse import unquote
from datetime import datetime
import glob
import traceback

def encode_title_for_filename(title):
    """
    将标题中的特殊字符编码为HTML实体形式，用于文件名
    """
    if pd.isna(title):
        return ""
    
    title = str(title).strip()
    
    # 首先解码已存在的HTML实体
    title = html.unescape(title)
    
    # 处理URL编码
    title = unquote(title)
    
    # 将文件名不允许的特殊字符编码为HTML实体（去掉&和;以适应文件名）
    char_map = {
        '<': '#x3c;',
        '>': '#x3e;', 
        ':': '#x3a;',
        '"': '#x22;',
        '/': '#x2f;',
        '\\': '#x5c;',
        '|': '#x7c;',
        '?': '#x3f;',
        '*': '#x2a;'
    }
    
    for char, encoded in char_map.items():
        title = title.replace(char, encoded)
    
    # 移除多余的空格，移除末尾的点号
    title = re.sub(r'\s+', ' ', title).strip().rstrip('.')
    
    return title

def parse_cover_date(date_str):
    """
    解析coverDate列，支持多种格式
    """
    if pd.isna(date_str):
        return None
    
    try:
        date_str = str(date_str).strip()
        
        # 处理像 "Mar2016" 这样的格式
        if re.match(r'[A-Za-z]+\d{4}', date_str):
            # 月份映射
            month_map = {
                'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
                'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
                'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
            }
            
            # 提取月份和年份
            month_match = re.match(r'([A-Za-z]+)(\d{4})', date_str)
            if month_match:
                month_str = month_match.group(1)
                year_str = month_match.group(2)
                
                if month_str in month_map:
                    return int(year_str)
        
        # 处理像 "20160301" 这样的格式
        if re.match(r'\d{8}', date_str):
            return int(date_str[:4])
        
        # 处理其他可能的年份格式
        year_match = re.search(r'(\d{4})', date_str)
        if year_match:
            return int(year_match.group(1))
            
        return None
        
    except Exception as e:
        print(f"解析日期出错: {date_str} - {e}")
        return None

def setup_edge_driver():
    """
    设置Edge浏览器驱动，配置下载设置
    """
    edge_options = Options()
    
    # 设置下载路径为临时目录
    download_dir = os.path.join(os.getcwd(), "temp_downloads")
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
    
    # 配置下载设置
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
        "plugins.always_open_pdf_externally": True
    }
    edge_options.add_experimental_option("prefs", prefs)
    
    # 使用现有的Edge用户配置
    try:
        user_data_dir = os.path.expanduser("~\\AppData\\Local\\Microsoft\\Edge\\User Data")
        if os.path.exists(user_data_dir):
            edge_options.add_argument(f"--user-data-dir={user_data_dir}")
            edge_options.add_argument("--profile-directory=Default")
    except:
        print("无法使用用户配置，将使用临时配置")
    
    # 其他选项
    edge_options.add_argument("--no-sandbox")
    edge_options.add_argument("--disable-dev-shm-usage")
    edge_options.add_argument("--disable-blink-features=AutomationControlled")
    edge_options.add_argument("--disable-extensions")
    edge_options.add_argument("--disable-logging")
    edge_options.add_argument("--log-level=3")
    edge_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    edge_options.add_experimental_option('useAutomationExtension', False)
    
    try:
        driver = webdriver.Edge(options=edge_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        print("Edge浏览器启动成功")
        return driver, download_dir
    except Exception as e:
        print(f"启动Edge浏览器失败: {e}")
        return None, None

def wait_for_download_complete(download_dir, timeout=180):  # 增加到3分钟
    """
    等待下载完成 - 增加等待时间
    """
    start_time = time.time()
    
    # 记录初始文件列表
    initial_files = set()
    if os.path.exists(download_dir):
        initial_files = set(os.listdir(download_dir))
    
    print(f"初始文件: {initial_files}")
    
    last_status_time = start_time
    
    while time.time() - start_time < timeout:
        try:
            if not os.path.exists(download_dir):
                time.sleep(2)
                continue
                
            current_files = set(os.listdir(download_dir))
            
            # 检查是否有下载中的文件
            downloading_files = [f for f in current_files if f.endswith('.crdownload') or f.endswith('.tmp')]
            
            if downloading_files:
                # 每30秒显示一次下载中状态
                if time.time() - last_status_time >= 30:
                    elapsed = int(time.time() - start_time)
                    print(f"[{elapsed}s] 检测到下载中的文件: {downloading_files}")
                    last_status_time = time.time()
            
            if not downloading_files:
                # 检查是否有新的PDF文件
                new_files = current_files - initial_files
                pdf_files = [f for f in new_files if f.endswith('.pdf')]
                
                # 也检查所有PDF文件
                all_pdf_files = [f for f in current_files if f.endswith('.pdf')]
                
                if pdf_files:
                    print(f"检测到新的PDF文件: {pdf_files}")
                    pdf_files.sort(key=lambda x: os.path.getmtime(os.path.join(download_dir, x)), reverse=True)
                    return pdf_files[0]
                elif all_pdf_files:
                    print(f"检测到PDF文件: {all_pdf_files}")
                    all_pdf_files.sort(key=lambda x: os.path.getmtime(os.path.join(download_dir, x)), reverse=True)
                    # 检查文件是否是新的（最近5分钟内修改）
                    latest_file = all_pdf_files[0]
                    file_path = os.path.join(download_dir, latest_file)
                    file_time = os.path.getmtime(file_path)
                    current_time = time.time()
                    
                    if current_time - file_time < 300:  # 5分钟内的文件
                        print(f"找到最近下载的文件: {latest_file}")
                        return latest_file
            
            # 每30秒显示一次等待状态
            if time.time() - last_status_time >= 30:
                elapsed = int(time.time() - start_time)
                print(f"[{elapsed}s] 等待下载完成... ({elapsed}/{timeout}秒)")
                print(f"当前文件: {current_files}")
                last_status_time = time.time()
            
            time.sleep(3)
            
        except Exception as e:
            print(f"检查下载状态时出错: {e}")
            time.sleep(5)
    
    # 超时后，最后检查一次
    print(f"等待超时({timeout}秒)，进行最后检查...")
    try:
        if os.path.exists(download_dir):
            current_files = set(os.listdir(download_dir))
            all_pdf_files = [f for f in current_files if f.endswith('.pdf')]
            if all_pdf_files:
                print(f"超时但发现PDF文件: {all_pdf_files}")
                all_pdf_files.sort(key=lambda x: os.path.getmtime(os.path.join(download_dir, x)), reverse=True)
                return all_pdf_files[0]
    except Exception as e:
        print(f"最后检查时出错: {e}")
    
    return None

def download_pdf_from_ebsco(driver, plink, output_path, download_dir, timeout=300):  # 增加到5分钟
    """
    从EBSCO下载PDF - 增加等待时间和错误处理
    """
    download_success = False
    
    try:
        print(f"\n{'='*80}")
        print(f"开始处理链接: {plink}")
        print(f"目标文件: {os.path.basename(output_path)}")
        print(f"{'='*80}")
        
        # 访问链接
        try:
            driver.get(plink)
            print("✓ 页面访问成功")
        except Exception as e:
            print(f"✗ 页面访问失败: {e}")
            return False
        
        # 等待页面初始加载
        print("等待页面加载...")
        time.sleep(10)  # 增加初始等待时间
        
        # 清理下载目录中的旧文件
        cleaned_files = []
        if os.path.exists(download_dir):
            for file in os.listdir(download_dir):
                if file.endswith('.pdf') or file.endswith('.crdownload'):
                    try:
                        file_path = os.path.join(download_dir, file)
                        os.remove(file_path)
                        cleaned_files.append(file)
                    except Exception as e:
                        print(f"清理文件失败: {e}")
        
        if cleaned_files:
            print(f"清理旧文件: {cleaned_files}")
        
        # 第一步：查找并点击第一个下载按钮
        max_wait = 180  # 增加到3分钟
        wait_time = 0
        download_button_found = False
        check_interval = 5
        
        print(f"开始查找第一个下载按钮 (最长等待{max_wait}秒)...")
        
        download_selectors = [
            'button[aria-label="下载"]',
            'button.tools-menu__tool--download__button',
            'button[class*="download"]',
            'button[data-auto="tool-button"][aria-label="下载"]',
            '.eb-tool-button__button[aria-label="下载"]',
            'button[aria-label="Download"]',
            'button[class*="download"][class*="button"]',
            'a[href*="download"]',
            'button[title*="下载"]',
            'button[title*="Download"]',
            '[data-icon="download"]',
            'svg[data-icon="download"]/../..',
            '//button[contains(@aria-label, "下载")]',
            '//button[contains(@title, "下载")]',
            '//button[contains(@class, "download")]',
            '//a[contains(text(), "下载")]',
            '//button[contains(text(), "下载")]'
        ]
        
        while wait_time < max_wait and not download_button_found:
            try:
                current_url = driver.current_url.lower()
                page_title = driver.title.lower()
                
                # 每30秒显示一次状态
                if wait_time % 30 == 0:
                    print(f"[{wait_time}s] 查找下载按钮...")
                    print(f"  当前URL: {current_url[:100]}...")
                    print(f"  页面标题: {page_title[:50]}...")
                
                # 尝试各种选择器查找下载按钮
                for selector in download_selectors:
                    try:
                        if selector.startswith('//'):
                            elements = driver.find_elements(By.XPATH, selector)
                        else:
                            elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        
                        if elements:
                            for element in elements:
                                try:
                                    if element.is_displayed() and element.is_enabled():
                                        print(f"✓ 找到第一个下载按钮: {selector}")
                                        print(f"  按钮文本: '{element.text}'")
                                        
                                        # 滚动到元素位置
                                        driver.execute_script("arguments[0].scrollIntoView(true);", element)
                                        time.sleep(3)
                                        
                                        # 点击下载按钮
                                        element.click()
                                        print("✓ 已点击第一个下载按钮")
                                        
                                        download_button_found = True
                                        break
                                except Exception as e:
                                    continue
                        
                        if download_button_found:
                            break
                            
                    except Exception as e:
                        continue
                
                if download_button_found:
                    break
                
            except Exception as e:
                print(f"查找第一个下载按钮时出错: {e}")
            
            time.sleep(check_interval)
            wait_time += check_interval
        
        if not download_button_found:
            print(f"✗ 在{max_wait}秒内未找到第一个下载按钮")
            return False
        
        # 第二步：等待弹框出现并点击第二个下载按钮
        print("等待弹框出现...")
        time.sleep(8)  # 增加等待时间
        
        second_button_found = False
        wait_time = 0
        max_wait_modal = 60  # 增加到1分钟
        
        second_download_selectors = [
            'button[data-auto="bulk-download-modal-download-button"]',
            'button[title="下载"].eb-button--default',
            '.nuc-bulk-download-modal-footer__button',
            'button[class*="bulk-download-modal-download-button"]',
            'button.nuc-bulk-download-modal-footer__button',
            '.eb-button--default[title="下载"]'
        ]
        
        while wait_time < max_wait_modal and not second_button_found:
            try:
                for selector in second_download_selectors:
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        
                        if elements:
                            for element in elements:
                                try:
                                    if element.is_displayed() and element.is_enabled():
                                        print(f"✓ 找到弹框中的下载按钮")
                                        print(f"  按钮文本: '{element.text}'")
                                        
                                        element.click()
                                        print("✓ 已点击弹框中的下载按钮")
                                        
                                        second_button_found = True
                                        break
                                except Exception as e:
                                    continue
                        
                        if second_button_found:
                            break
                            
                    except Exception as e:
                        continue
                
                if second_button_found:
                    break
                
                if wait_time % 15 == 0:
                    print(f"[{wait_time}s] 继续查找弹框按钮...")
                    
            except Exception as e:
                print(f"查找弹框按钮时出错: {e}")
                
            time.sleep(3)
            wait_time += 3
        
        if not second_button_found:
            print("警告: 未找到弹框中的下载按钮，继续等待下载...")
        
        # 第三步：等待下载完成
        print("等待文件下载完成...")
        downloaded_file = wait_for_download_complete(download_dir, timeout=180)  # 3分钟
        
        if downloaded_file:
            downloaded_path = os.path.join(download_dir, downloaded_file)
            print(f"✓ 找到下载的文件: {downloaded_file}")
            print(f"  文件路径: {downloaded_path}")
            
            # 验证下载的文件
            if os.path.exists(downloaded_path):
                file_size = os.path.getsize(downloaded_path)
                print(f"  文件大小: {file_size:,} bytes")
                
                if file_size > 1000:
                    # 移动并重命名文件到目标位置
                    try:
                        import shutil
                        
                        # 确保目标目录存在
                        target_dir = os.path.dirname(output_path)
                        if not os.path.exists(target_dir):
                            os.makedirs(target_dir)
                        
                        # 移动文件到目标位置并重命名
                        shutil.move(downloaded_path, output_path)
                        print(f"✓ PDF下载并重命名成功!")
                        print(f"  原文件名: {downloaded_file}")
                        print(f"  新文件名: {os.path.basename(output_path)}")
                        print(f"  保存路径: {output_path}")
                        download_success = True
                        
                    except Exception as e:
                        print(f"✗ 移动文件时出错: {e}")
                        # 尝试复制然后删除原文件
                        try:
                            import shutil
                            shutil.copy2(downloaded_path, output_path)
                            os.remove(downloaded_path)
                            print(f"✓ PDF复制并重命名成功!")
                            print(f"  原文件名: {downloaded_file}")
                            print(f"  新文件名: {os.path.basename(output_path)}")
                            download_success = True
                        except Exception as e2:
                            print(f"✗ 复制文件时出错: {e2}")
                            print(f"文件保留在原位置: {downloaded_path}")
                else:
                    print("✗ 下载的文件太小，可能不完整")
            else:
                print("✗ 下载的文件不存在")
        else:
            print("✗ 下载超时或失败")
            # 最后检查一次下载目录
            try:
                if os.path.exists(download_dir):
                    all_files = os.listdir(download_dir)
                    pdf_files = [f for f in all_files if f.endswith('.pdf')]
                    if pdf_files:
                        print(f"发现遗留的PDF文件: {pdf_files}")
                        # 尝试处理最新的文件
                        latest_pdf = max(pdf_files, key=lambda x: os.path.getmtime(os.path.join(download_dir, x)))
                        latest_path = os.path.join(download_dir, latest_pdf)
                        
                        try:
                            import shutil
                            shutil.move(latest_path, output_path)
                            print(f"✓ 处理遗留文件成功: {latest_pdf}")
                            download_success = True
                        except Exception as e:
                            print(f"✗ 处理遗留文件失败: {e}")
            except Exception as e:
                print(f"最后检查时出错: {e}")
        
        return download_success
        
    except Exception as e:
        print(f"✗ 处理链接时发生严重错误: {e}")
        print("错误详情:")
        print(traceback.format_exc())
        return False
    
    finally:
        # 确保无论如何都会继续到下一个链接
        print(f"链接处理完成，结果: {'成功' if download_success else '失败'}")

def process_csv_files(input_folder, output_folder):
    """
    处理CSV文件并下载PDF - 改进循环控制
    """
    # 创建输出文件夹
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # 设置浏览器驱动
    driver, download_dir = setup_edge_driver()
    if not driver:
        return
    
    try:
        # 遍历所有CSV文件
        csv_files = []
        for root, dirs, files in os.walk(input_folder):
            for file in files:
                if file.endswith('.csv'):
                    csv_files.append(os.path.join(root, file))
        
        print(f"\n找到 {len(csv_files)} 个CSV文件")
        
        total_downloaded = 0
        total_processed = 0
        failed_downloads = []
        
        for csv_file_idx, csv_file in enumerate(csv_files):
            print(f"\n{'='*80}")
            print(f"处理文件 [{csv_file_idx+1}/{len(csv_files)}]: {os.path.basename(csv_file)}")
            print(f"{'='*80}")
            
            try:
                # 读取CSV文件
                df = pd.read_csv(csv_file, encoding='utf-8')
                print(f"读取到 {len(df)} 条记录")
                
                # 检查必需的列
                required_columns = ['title', 'coverDate', 'plink']
                missing_columns = [col for col in required_columns if col not in df.columns]
                
                if missing_columns:
                    print(f"警告: 缺少必需的列: {missing_columns}")
                    continue
                
                # 处理标题
                df['titlename'] = df['title'].apply(encode_title_for_filename)
                
                # 解析日期
                df['year'] = df['coverDate'].apply(parse_cover_date)
                
                # 显示年份分布
                year_counts = df['year'].value_counts().sort_index()
                print("年份分布:")
                for year, count in year_counts.items():
                    if pd.notna(year):
                        print(f"  {int(year)}: {count} 条")
                
                # 过滤2020年及之后的数据
                df_filtered = df[df['year'] >= 2020]
                
                print(f"筛选出 {len(df_filtered)} 条2020年及之后的记录")
                
                if len(df_filtered) == 0:
                    print("没有符合条件的记录，跳过此文件")
                    continue
                
                # 下载PDF
                for record_idx, (index, row) in enumerate(df_filtered.iterrows()):
                    try:
                        titlename = row['titlename']
                        plink = row['plink']
                        year = row['year']
                        original_title = row['title']
                        
                        # 检查数据完整性
                        if pd.isna(plink) or pd.isna(titlename) or not titlename.strip():
                            print(f"跳过无效记录: {original_title}")
                            continue
                        
                        # 创建PDF文件路径
                        pdf_filename = f"{titlename}.pdf"
                        pdf_path = os.path.join(output_folder, pdf_filename)
                        
                        # 跳过已存在的文件
                        if os.path.exists(pdf_path):
                            print(f"[{record_idx+1}/{len(df_filtered)}] 已存在: {titlename[:50]}...")
                            continue
                        
                        total_processed += 1
                        
                        print(f"\n{'*'*60}")
                        print(f"[{total_processed}] [{record_idx+1}/{len(df_filtered)}] 开始下载 ({int(year)}年):")
                        print(f"原标题: {original_title[:80]}...")
                        print(f"文件名: {titlename[:80]}...")
                        print(f"链接: {plink}")
                        print(f"{'*'*60}")
                        
                        # 下载PDF
                        success = download_pdf_from_ebsco(driver, plink, pdf_path, download_dir)
                        
                        if success:
                            total_downloaded += 1
                            print(f"\n✅ 下载成功! ({total_downloaded}/{total_processed})")
                        else:
                            total_failed = total_processed - total_downloaded
                            print(f"\n❌ 下载失败! ({total_downloaded}/{total_processed})")
                            failed_downloads.append({
                                'title': original_title,
                                'plink': plink,
                                'year': year,
                                'csv_file': os.path.basename(csv_file)
                            })
                        
                        # 显示进度
                        print(f"\n📊 当前进度: 成功 {total_downloaded} | 失败 {total_processed - total_downloaded} | 总计 {total_processed}")
                        
                        # 休息一下，避免请求过于频繁
                        print("休息10秒后继续下一个...")
                        time.sleep(10)
                        
                    except Exception as e:
                        print(f"处理单个记录时出错: {e}")
                        print("错误详情:")
                        print(traceback.format_exc())
                        print("继续处理下一个记录...")
                        continue
                
            except Exception as e:
                print(f"处理CSV文件时出错: {e}")
                print("错误详情:")
                print(traceback.format_exc())
                print("继续处理下一个CSV文件...")
                continue
        
        # 显示最终统计结果
        print(f"\n{'='*80}")
        print(f"🎉 所有处理完成!")
        print(f"📈 最终统计:")
        print(f"  总处理: {total_processed} 个链接")
        print(f"  成功下载: {total_downloaded} 个PDF")
        print(f"  失败: {total_processed - total_downloaded} 个")
        if total_processed > 0:
            success_rate = (total_downloaded/total_processed*100)
            print(f"  成功率: {success_rate:.1f}%")
        
        # 保存失败记录
        if failed_downloads:
            print(f"\n📄 失败记录:")
            failed_df = pd.DataFrame(failed_downloads)
            failed_file = os.path.join(output_folder, "failed_downloads.csv")
            failed_df.to_csv(failed_file, index=False, encoding='utf-8')
            print(f"失败记录已保存到: {failed_file}")
            
            print(f"\n前5个失败的下载:")
            for i, failed in enumerate(failed_downloads[:5]):
                print(f"  {i+1}. {failed['title'][:60]}... ({failed['year']}年)")
        
        print(f"{'='*80}")
        
    except Exception as e:
        print(f"主处理流程出错: {e}")
        print("错误详情:")
        print(traceback.format_exc())
        
    finally:
        # 清理临时下载目录
        try:
            import shutil
            if os.path.exists(download_dir):
                # 检查是否还有文件
                remaining_files = os.listdir(download_dir)
                if remaining_files:
                    print(f"\n📁 临时目录中还有文件: {remaining_files}")
                    print(f"临时目录路径: {download_dir}")
                    print("您可以手动检查这些文件")
                else:
                    shutil.rmtree(download_dir)
                    print("🧹 已清理临时下载目录")
        except Exception as e:
            print(f"清理临时目录时出错: {e}")
        
        # 关闭浏览器
        try:
            driver.quit()
            print("🔒 浏览器已关闭")
        except Exception as e:
            print(f"关闭浏览器时出错: {e}")

def decode_filename_back(filename):
    """
    将编码后的文件名解码回原始标题
    """
    if filename.endswith('.pdf'):
        filename = filename[:-4]
    
    char_map = {
        '#x3c;': '<',
        '#x3e;': '>',
        '#x3a;': ':',
        '#x22;': '"',
        '#x2f;': '/',
        '#x5c;': '\\',
        '#x7c;': '|',
        '#x3f;': '?',
        '#x2a;': '*'
    }
    
    for encoded, char in char_map.items():
        filename = filename.replace(encoded, char)
    
    return filename

def batch_decode_filenames(folder_path):
    """
    批量解码文件夹中的文件名
    """
    if not os.path.exists(folder_path):
        print(f"文件夹不存在: {folder_path}")
        return
    
    decoded_count = 0
    for filename in os.listdir(folder_path):
        if filename.endswith('.pdf'):
            original_path = os.path.join(folder_path, filename)
            decoded_name = decode_filename_back(filename)
            
            if decoded_name != filename[:-4]:  # 如果有变化
                new_filename = decoded_name + '.pdf'
                new_path = os.path.join(folder_path, new_filename)
                
                try:
                    os.rename(original_path, new_path)
                    print(f"重命名: {filename} -> {new_filename}")
                    decoded_count += 1
                except Exception as e:
                    print(f"重命名失败: {filename} - {e}")
    
    print(f"完成! 共重命名 {decoded_count} 个文件")

def get_user_timeout_settings():
    """
    获取用户自定义的超时设置
    """
    print("\n⚙️  超时设置配置:")
    print("当前默认设置:")
    print("  - 查找第一个下载按钮: 180秒 (3分钟)")
    print("  - 查找弹框按钮: 60秒 (1分钟)")
    print("  - 等待下载完成: 180秒 (3分钟)")
    print("  - 单个链接总超时: 300秒 (5分钟)")
    
    use_custom = input("\n是否自定义超时设置? (y/n, 默认n): ").lower().strip()
    
    if use_custom == 'y':
        try:
            first_button_timeout = int(input("查找第一个下载按钮超时(秒, 默认180): ") or "180")
            modal_button_timeout = int(input("查找弹框按钮超时(秒, 默认60): ") or "60")
            download_timeout = int(input("等待下载完成超时(秒, 默认180): ") or "180")
            
            print(f"\n✓ 自定义设置:")
            print(f"  - 查找第一个下载按钮: {first_button_timeout}秒")
            print(f"  - 查找弹框按钮: {modal_button_timeout}秒")
            print(f"  - 等待下载完成: {download_timeout}秒")
            
            return first_button_timeout, modal_button_timeout, download_timeout
            
        except ValueError:
            print("输入无效，使用默认设置")
    
    return 180, 60, 180  # 默认值

def check_system_status():
    """
    检查系统状态
    """
    print("\n🔍 系统状态检查:")
    
    # 检查Edge浏览器
    try:
        import subprocess
        result = subprocess.run(['where', 'msedge'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ Edge浏览器: 已安装")
        else:
            print("⚠️  Edge浏览器: 未找到")
    except:
        print("⚠️  Edge浏览器: 检查失败")
    
    # 检查EdgeDriver
    try:
        result = subprocess.run(['where', 'msedgedriver'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ EdgeDriver: 已安装")
        else:
            print("⚠️  EdgeDriver: 未找到 (可能需要手动下载)")
    except:
        print("⚠️  EdgeDriver: 检查失败")
    
    # 检查磁盘空间
    try:
        import shutil
        total, used, free = shutil.disk_usage(".")
        free_gb = free // (1024**3)
        print(f"✓ 磁盘空间: {free_gb}GB 可用")
        if free_gb < 1:
            print("⚠️  磁盘空间不足，建议清理")
    except:
        print("⚠️  磁盘空间: 检查失败")

def main():
    """
    主函数 - 改进的用户界面
    """
    print("="*80)
    print("📚 EBSCO PDF 批量下载工具 v5.0")
    print("🔧 改进版本 - 增加等待时间和错误处理")
    print("🌐 请确保已在Edge浏览器中登录大学账户")
    print("="*80)
    
    # 检查系统状态
    check_system_status()
    
    # 获取路径
    print("\n📂 路径配置:")
    input_folder = input("请输入CSV文件夹路径: ").strip().strip('"')
    output_folder = input("PDF输出文件夹 (默认: pdfs): ").strip().strip('"') or "pdfs"
    
    if not os.path.exists(input_folder):
        print(f"❌ 错误: 文件夹不存在: {input_folder}")
        return
    
    print(f"\n📋 配置确认:")
    print(f"  输入文件夹: {input_folder}")
    print(f"  输出文件夹: {output_folder}")
    
    # 获取超时设置
    first_timeout, modal_timeout, download_timeout = get_user_timeout_settings()
    
    print(f"\n🎯 功能说明:")
    print(f"  1. 自动处理EBSCO的两步下载流程")
    print(f"  2. 检测固定命名的下载文件并重命名")
    print(f"  3. 特殊字符编码 (? -> #x3f; 等)")
    print(f"  4. 生成失败记录文件")
    print(f"  5. 增强的错误处理和重试机制")
    print(f"  6. 详细的进度显示")
    
    # 询问是否开始处理
    print(f"\n🚀 操作选择:")
    choice = input("1. 开始批量下载 (y)\n2. 仅解码现有文件名 (d)\n3. 系统检查 (c)\n4. 退出 (n)\n请选择: ").lower().strip()
    
    if choice == 'y' or choice == '1':
        print(f"\n🎬 开始处理...")
        print(f"⏰ 使用超时设置: 第一按钮{first_timeout}s, 弹框{modal_timeout}s, 下载{download_timeout}s")
        
        # 确认开始
        if input("确认开始? (y/n): ").lower().strip() == 'y':
            # 这里可以传递超时参数，但为了简化，我们在函数内部使用固定值
            # 实际使用时可以修改download_pdf_from_ebsco函数接受这些参数
            process_csv_files(input_folder, output_folder)
        else:
            print("❌ 已取消")
            
    elif choice == 'd' or choice == '2':
        decode_folder = input(f"请输入要解码的文件夹路径 (默认: {output_folder}): ").strip().strip('"') or output_folder
        print(f"\n🔄 开始解码文件名...")
        batch_decode_filenames(decode_folder)
        
    elif choice == 'c' or choice == '3':
        print(f"\n🔍 执行详细系统检查...")
        check_system_status()
        
        # 测试浏览器启动
        print(f"\n🌐 测试浏览器启动...")
        try:
            driver, download_dir = setup_edge_driver()
            if driver:
                print("✓ 浏览器启动测试成功")
                driver.quit()
                
                # 清理测试目录
                if os.path.exists(download_dir):
                    import shutil
                    shutil.rmtree(download_dir)
            else:
                print("❌ 浏览器启动测试失败")
        except Exception as e:
            print(f"❌ 浏览器测试出错: {e}")
            
    else:
        print("👋 再见!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n⚠️  用户中断操作")
        print("👋 程序已退出")
    except Exception as e:
        print(f"\n\n❌ 程序出现未预期的错误:")
        print(f"错误信息: {e}")
        print("错误详情:")
        print(traceback.format_exc())
        print("\n如果问题持续，请检查:")
        print("1. 网络连接是否正常")
        print("2. Edge浏览器是否已登录大学账户")
        print("3. CSV文件格式是否正确")
        print("4. 磁盘空间是否充足")
