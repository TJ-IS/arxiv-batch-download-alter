import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
import time
import html
import re
from urllib.parse import unquote
import traceback

def encode_title_for_filename(title):
    """
    将标题中的特殊字符编码为HTML实体形式，用于文件名
    """
    if pd.isna(title):
        return "untitled"
    
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
    
    # 限制文件名长度
    if len(title) > 200:
        title = title[:200]
    
    return title

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

def wait_for_download_complete(download_dir, timeout=180):
    """
    等待下载完成
    """
    start_time = time.time()
    
    # 记录初始文件列表
    initial_files = set()
    if os.path.exists(download_dir):
        initial_files = set(os.listdir(download_dir))
    
    print(f"等待下载完成...")
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
                    print(f"  [{elapsed}s] 正在下载: {downloading_files[0]}")
                    last_status_time = time.time()
            
            if not downloading_files:
                # 检查是否有新的PDF文件
                new_files = current_files - initial_files
                pdf_files = [f for f in new_files if f.endswith('.pdf')]
                
                if pdf_files:
                    print(f"  检测到新的PDF文件: {pdf_files[0]}")
                    pdf_files.sort(key=lambda x: os.path.getmtime(os.path.join(download_dir, x)), reverse=True)
                    return pdf_files[0]
                
                # 也检查所有PDF文件（防止遗漏）
                all_pdf_files = [f for f in current_files if f.endswith('.pdf')]
                if all_pdf_files:
                    all_pdf_files.sort(key=lambda x: os.path.getmtime(os.path.join(download_dir, x)), reverse=True)
                    latest_file = all_pdf_files[0]
                    file_path = os.path.join(download_dir, latest_file)
                    file_time = os.path.getmtime(file_path)
                    current_time = time.time()
                    
                    # 检查文件是否是最近的（5分钟内）
                    if current_time - file_time < 300:
                        print(f"  找到最近下载的文件: {latest_file}")
                        return latest_file
            
            time.sleep(3)
            
        except Exception as e:
            print(f"  检查下载状态时出错: {e}")
            time.sleep(5)
    
    print(f"  下载等待超时({timeout}秒)")
    return None

def download_pdf_from_informs(driver, pdf_link, output_path, download_dir):
    """
    从INFORMS下载PDF - 简化版本
    """
    download_success = False
    
    try:
        print(f"\n访问链接: {pdf_link}")
        
        # 访问链接
        try:
            driver.get(pdf_link)
            print("✓ 页面访问成功")
        except Exception as e:
            print(f"✗ 页面访问失败: {e}")
            return False
        
        # 等待页面加载
        time.sleep(8)
        
        # 清理下载目录中的旧文件
        if os.path.exists(download_dir):
            for file in os.listdir(download_dir):
                if file.endswith('.pdf') or file.endswith('.crdownload'):
                    try:
                        os.remove(os.path.join(download_dir, file))
                    except:
                        pass
        
        # 查找并点击INFORMS的下载按钮
        print("查找下载按钮...")
        
        download_selectors = [
            # INFORMS特定的下载按钮选择器
            'a[data-download-files-key="pdf"][data-original-title="Download"]',
            'a[data-download-files-key="pdf"]',
            'a[aria-label*="Download PDF"]',
            'a.navbar-download.btn.btn--cta_roundedColored',
            'a[href*="download=true"]',
            'a[target="_blank"][href*="/doi/pdf/"]',
            'button[data-download-files-key="pdf"]',
            'a[class*="download"][class*="btn"]',
            '.navbar-download',
            '[data-single-download="true"]'
        ]
        
        download_button_found = False
        max_attempts = 12  # 最多尝试60秒 (12 * 5秒)
        
        for attempt in range(max_attempts):
            for selector in download_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    if elements:
                        for element in elements:
                            try:
                                if element.is_displayed() and element.is_enabled():
                                    print(f"✓ 找到下载按钮: {selector}")
                                    
                                    # 滚动到元素位置
                                    driver.execute_script("arguments[0].scrollIntoView(true);", element)
                                    time.sleep(2)
                                    
                                    # 点击下载按钮
                                    element.click()
                                    print("✓ 已点击下载按钮")
                                    
                                    download_button_found = True
                                    break
                            except:
                                continue
                    
                    if download_button_found:
                        break
                        
                except:
                    continue
            
            if download_button_found:
                break
            
            if attempt < max_attempts - 1:
                print(f"  尝试 {attempt + 1}/{max_attempts}，等待5秒后重试...")
                time.sleep(5)
        
        if not download_button_found:
            print("✗ 未找到下载按钮")
            return False
        
        # 等待下载完成
        downloaded_file = wait_for_download_complete(download_dir, timeout=120)
        
        if downloaded_file:
            downloaded_path = os.path.join(download_dir, downloaded_file)
            
            if os.path.exists(downloaded_path):
                file_size = os.path.getsize(downloaded_path)
                print(f"  文件大小: {file_size:,} bytes")
                
                if file_size > 1000:  # 文件大小合理
                    try:
                        import shutil
                        
                        # 确保目标目录存在
                        target_dir = os.path.dirname(output_path)
                        if not os.path.exists(target_dir):
                            os.makedirs(target_dir)
                        
                        # 移动文件到目标位置并重命名
                        shutil.move(downloaded_path, output_path)
                        print(f"✓ PDF下载成功: {os.path.basename(output_path)}")
                        download_success = True
                        
                    except Exception as e:
                        print(f"✗ 移动文件时出错: {e}")
                else:
                    print("✗ 下载的文件太小，可能不完整")
            else:
                print("✗ 下载的文件不存在")
        else:
            print("✗ 下载失败或超时")
        
        return download_success
        
    except Exception as e:
        print(f"✗ 处理链接时发生错误: {e}")
        return False

def process_csv_files(input_folder, output_folder):
    """
    处理CSV文件并下载PDF - 简化版本
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
                if 'Title' not in df.columns:
                    print(f"警告: 缺少Title列，将使用序号命名")
                    df['Title'] = df.index.astype(str)
                
                if 'PDF_Link' not in df.columns:
                    print(f"错误: 缺少PDF_Link列，跳过此文件")
                    continue
                
                # 处理标题
                df['titlename'] = df['Title'].apply(encode_title_for_filename)
                
                # 过滤掉无效的链接
                df_filtered = df[df['PDF_Link'].notna() & (df['PDF_Link'] != '')]
                
                print(f"有效链接: {len(df_filtered)} 条")
                
                if len(df_filtered) == 0:
                    print("没有有效的链接，跳过此文件")
                    continue
                
                # 下载PDF
                for record_idx, (index, row) in enumerate(df_filtered.iterrows()):
                    try:
                        titlename = row['titlename']
                        pdf_link = row['PDF_Link']
                        original_title = row['Title']
                        
                        # 创建PDF文件路径
                        pdf_filename = f"{titlename}.pdf"
                        pdf_path = os.path.join(output_folder, pdf_filename)
                        
                        # 跳过已存在的文件
                        if os.path.exists(pdf_path):
                            print(f"[{record_idx+1}/{len(df_filtered)}] 已存在，跳过: {titlename[:50]}...")
                            continue
                        
                        total_processed += 1
                        
                        print(f"\n{'*'*60}")
                        print(f"[{total_processed}] [{record_idx+1}/{len(df_filtered)}] 开始下载:")
                        print(f"标题: {original_title[:80]}...")
                        print(f"文件名: {titlename[:80]}...")
                        print(f"{'*'*60}")
                        
                        # 下载PDF
                        success = download_pdf_from_informs(driver, pdf_link, pdf_path, download_dir)
                        
                        if success:
                            total_downloaded += 1
                            print(f"✅ 下载成功! ({total_downloaded}/{total_processed})")
                        else:
                            print(f"❌ 下载失败! ({total_downloaded}/{total_processed})")
                            failed_downloads.append({
                                'title': original_title,
                                'pdf_link': pdf_link,
                                'csv_file': os.path.basename(csv_file)
                            })
                        
                        # 显示进度
                        success_rate = (total_downloaded/total_processed*100) if total_processed > 0 else 0
                        print(f"📊 当前进度: 成功 {total_downloaded} | 失败 {total_processed - total_downloaded} | 成功率 {success_rate:.1f}%")
                        
                        # 休息一下
                        print("休息8秒后继续...")
                        time.sleep(8)
                        
                    except Exception as e:
                        print(f"处理单个记录时出错: {e}")
                        continue
                
            except Exception as e:
                print(f"处理CSV文件时出错: {e}")
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
            failed_df = pd.DataFrame(failed_downloads)
            failed_file = os.path.join(output_folder, "failed_downloads.csv")
            failed_df.to_csv(failed_file, index=False, encoding='utf-8')
            print(f"\n失败记录已保存到: {failed_file}")
        
        print(f"{'='*80}")
        
    except Exception as e:
        print(f"主处理流程出错: {e}")
        print(traceback.format_exc())
        
    finally:
        # 清理临时下载目录
        try:
            import shutil
            if os.path.exists(download_dir):
                remaining_files = os.listdir(download_dir)
                if remaining_files:
                    print(f"\n临时目录中还有文件: {remaining_files}")
                    print(f"路径: {download_dir}")
                else:
                    shutil.rmtree(download_dir)
                    print("已清理临时下载目录")
        except Exception as e:
            print(f"清理临时目录时出错: {e}")
        
        # 关闭浏览器
        try:
            driver.quit()
            print("浏览器已关闭")
        except Exception as e:
            print(f"关闭浏览器时出错: {e}")

def main():
    """
    主函数 - 简化版本
    """
    print("="*80)
    print("📚 INFORMS PDF 批量下载工具 - 简化版")
    print("🔧 直接下载所有PDF_Link列中的链接")
    print("🌐 请确保已在Edge浏览器中登录大学账户")
    print("="*80)
    
    # 获取路径
    print("\n📂 路径配置:")
    input_folder = input("请输入CSV文件夹路径: ").strip().strip('"')
    output_folder = input("PDF输出文件夹 (默认: informs_pdfs): ").strip().strip('"') or "informs_pdfs"
    
    if not os.path.exists(input_folder):
        print(f"❌ 错误: 文件夹不存在: {input_folder}")
        return
    
    print(f"\n📋 配置确认:")
    print(f"  输入文件夹: {input_folder}")
    print(f"  输出文件夹: {output_folder}")
    
    print(f"\n🎯 功能说明:")
    print(f"  1. 读取CSV文件中的Title和PDF_Link列")
    print(f"  2. 直接下载所有有效的PDF链接")
    print(f"  3. 使用Title作为文件名（特殊字符编码处理）")
    print(f"  4. 跳过已存在的文件")
    print(f"  5. 生成失败记录文件")
    
    # 确认开始
    if input("\n🚀 确认开始下载? (y/n): ").lower().strip() == 'y':
        print(f"\n🎬 开始处理...")
        process_csv_files(input_folder, output_folder)
    else:
        print("❌ 已取消")

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
