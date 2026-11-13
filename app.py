import akshare as ak
import pandas as pd
import datetime
import os
import requests
import time
import math

# ==================== 配置区 ====================
SENDKEY = "SCT463844TNcz5U47QQNahk4owcCxxRGdV"
CSV_FILE = "trin_history.csv"
# ================================================

def get_spot_data():
    """
    终极多源获取：东财 -> 东财备用 -> 腾讯拼接
    """
    # 1. 尝试东方财富主接口
    try:
        print("正在尝试通过【东方财富主接口】抓取全市场数据...")
        df = ak.stock_zh_a_spot_em()
        if len(df) > 4000: # 确认抓到了全市场的数据
            print("✅ 东财主接口成功")
            return df
    except Exception as e:
        print(f"⚠️ 东财主接口失败: {e}")

    time.sleep(2)

    # 2. 尝试东方财富备用接口 (绕过限流)
    try:
        print("正在尝试通过【东方财富备用接口】抓取数据...")
        # 这是东财另一个常用的行情接口，数据格式极其相似
        df = ak.stock_zh_a_spot_em_v2() if hasattr(ak, 'stock_zh_a_spot_em_v2') else ak.stock_zh_a_spot_em()
        if len(df) > 4000:
            print("✅ 东财备用接口成功")
            return df
    except Exception as e:
        print(f"⚠️ 东财备用接口失败: {e}")

    time.sleep(2)

    # 3. 终极备胎：腾讯接口（逐页获取，几乎不封IP）
    try:
        print("正在尝试通过【腾讯分页接口】抓取数据（耗时较长，请耐心等待）...")
        # akshare 的腾讯接口
        df = ak.stock_zh_a_spot_qq()
        if len(df) > 4000:
            print("✅ 腾讯接口成功")
            return df
    except Exception as e:
        print(f"⚠️ 腾讯接口失败: {e}")

    # 全挂了的终极兜底
    raise RuntimeError("所有行情接口均被限流或失效，今日无法获取数据。")

def clean_and_standardize(df):
    """
    神仙级数据清洗：自动识别列名，自动对齐单位（元/万元），解决公式报错
    """
    # 1. 模糊匹配列名
    pct_col = next((c for c in df.columns if '涨跌幅' in c or c == 'pct_chg'), None)
    amt_col = next((c for c in df.columns if '成交额' in c or c in ['amount', 'turnover']), None)
    
    if not pct_col or not amt_col:
        raise ValueError("返回数据中找不到 涨跌幅 或 成交额 字段")

    # 2. 提取并重命名
    df = df[[pct_col, amt_col]].copy()
    df.columns = ['pct', 'amt']

    # 3. 强制转数字，剔除停牌等脏数据
    df['pct'] = pd.to_numeric(df['pct'], errors='coerce')
    df['amt'] = pd.to_numeric(df['amt'], errors='coerce')
    df = df.dropna(subset=['pct', 'amt'])

    # 4. 智能单位对齐 (极重要)
    # 全A股一天的总成交额通常在 5000亿 到 15000亿 之间。
    # 如果 sum 小于 100000000 (1个亿)，说明单位是“万元”，必须乘以 10000 变成“元”
    total_amt = df['amt'].sum()
    if total_amt < 100000000:
        print("🔍 检测到成交额单位为“万元”，正在自动转换为“元”...")
        df['amt'] = df['amt'] * 10000

    return df

def fetch_and_save():
    print(f"--- 开始执行数据抓取 ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ---")
    
    raw_df = get_spot_data()
    spot_df = clean_and_standardize(raw_df)

    # 分类统计
    up_df = spot_df[spot_df['pct'] > 0]
    down_df = spot_df[spot_df['pct'] < 0]
    
    up_count = len(up_df)
    down_count = len(down_df)
    up_amount = up_df['amt'].sum()
    down_amount = down_df['amt'].sum()

    # 计算 TRIN 
    if down_count == 0 or down_amount == 0:
        trin_val = 999.99 # 极端情况（全市场涨停）
    else:
        # 公式：(上涨家数 / 下跌家数) / (上涨成交额 / 下跌成交额)
        trin_val = (up_count / down_count) / (up_amount / down_amount)

    print(f"抓取完成: 上涨 {up_count} 家, 下跌 {down_count} 家, TRIN值: {trin_val:.2f}")
    
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    
    new_row = pd.DataFrame({
        'date': [today],
        'adv_count': [up_count],
        'dec_count': [down_count],
        'trin': [round(trin_val, 4)]
    })
    
    # 写入 CSV (自动去重)
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        # 如果今天已经有数据了，删掉旧的
        df = df[df['date'] != today]
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(CSV_FILE, index=False)
    else:
        new_row.to_csv(CSV_FILE, index=False)
        
    return up_count, down_count, trin_val

def send_wechat_text(adv_count=None, dec_count=None, trin_val=None):
    print("正在通过 Server酱 推送纯文本...")
    url = f"https://sctapi.ftqq.com/{SENDKEY}.send"
    
    if adv_count is not None and trin_val is not None:
        desp = f"### 今日 TRIN 数据更新\n\n"
        desp += f"- 最新原始 TRIN: **{trin_val:.2f}**\n"
        desp += f"- 上涨家数: **{adv_count}**\n"
        desp += f"- 下跌家数: **{dec_count}**\n"
        desp += f"\n*(注: 数据源已全自动适配)*"
    else:
        desp = "无数据"

    data = {
        "title": "A股 TRIN 监控日报",
        "desp": desp
    }
    
    res = requests.post(url, data=data).json()
    print("推送结果:", res)

def send_error_msg(error_msg):
    print("正在推送异常报警通知...")
    url = f"https://sctapi.ftqq.com/{SENDKEY}.send"
    data = {
        "title": "⚠️ TRIN 监控日报执行失败",
        "desp": f"### 执行失败\n\n今天的日报没有生成。\n\n**报错原因**：\n{error_msg}\n\n*请去 GitHub Actions 查看详细日志。*"
    }
    try:
        requests.post(url, data=data)
        print("已成功发送异常提醒。")
    except Exception as e:
        print(f"连异常提醒都发不出去: {e}")

if __name__ == "__main__":
    try:
        adv, dec, trin = fetch_and_save()
        send_wechat_text(adv, dec, trin)
    except Exception as e:
        error_info = str(e)
        print(f"执行出错: {error_info}")
        send_error_msg(error_info)
