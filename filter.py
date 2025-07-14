import pandas as pd
import re

def filter_comments(file_path, save_path=None):
    """
    从CSV文件中筛选符合条件的comment，并返回DataFrame。
    
    条件：
    - 包含 accept / publish / appear（子串匹配）
    - 或：包含 22/23/24/25，但：
        × 后面不能跟 pages/figures
        × 不能只出现在 arxiv 引用中（如 arxiv:2310.12345）
    """
    df_all = pd.read_csv(file_path, encoding = 'utf-8')
    df_all['comment'] = df_all['comment'].astype(str).str.lower()

    # 条件1：包含 accept / publish / appear
    condition1 = df_all['comment'].str.contains(r'accept|publish|appear')

    # 条件2：包含 22–25，且不是出现在 arxiv 引用中，且后面不是 pages/figures
    def match_condition2(comment):
        # 快速检测是否包含目标数字
        if not re.search(r'(22|23|24|25)', comment):
            return False

        # 1. 排除 pages / figures 的跟随
        if re.search(r'(22|23|24|25)\s*(pages|figures)', comment):
            return False

        # 2. 提取所有 arxiv 引用（如 arxiv:2310.12345）
        arxiv_matches = re.findall(r'arxiv:\s*\d+', comment)
        numbers_in_arxiv = set()
        for m in arxiv_matches:
            nums = re.findall(r'(22|23|24|25)', m)
            numbers_in_arxiv.update(nums)

        # 3. 查找出现在整段 comment 中的 22~25
        all_numbers_in_text = set(re.findall(r'(22|23|24|25)', comment))

        # 4. 如果所有命中的数字都只出现在 arxiv 引用中 → 排除
        if all_numbers_in_text.issubset(numbers_in_arxiv):
            return False

        # 保留其余情况
        return True

    condition2 = df_all['comment'].apply(match_condition2)

    # 合并条件
    df_filtered = df_all[condition1 | condition2]

    if save_path:
        df_filtered.to_csv(save_path, index=False, encoding='utf-8')

    return df_filtered



if __name__ == '__main__':
    print(filter_comments ('paper_result_no.csv', 'paper_result_no_filter.csv'))