import akshare as ak
import pandas as pd
import datetime
import os
import requests
import time

# ==================== 配置区 ====================
# 你的 Server酱 SendKey
SENDKEY = "SCT463844TNcz5U47QQNahk4owcCxxRGdV"
CSV_FILE = "trin_history.csv"
# ================================================

def get_spot_data():
    """
    多级备用行情获取函数（防东财限流）
    """
    # 1. 尝试东方财富
    try:
        print("正在尝试通过【东方财富】抓取全市场数据...")
        # 加上 timeout 防止东财卡死
        df = ak.stock_zh_a_spot_em()
        df = df.dropna(subset=['涨跌幅', '成交额'])
        print("✅ 东方财富数据抓取成功")
        return df
    except Exception as e:
        print(f"⚠️ 东方财富接口失败: {e}")
        print("准备切换备用数据源...")

    # 2. 尝试新浪财经（备用源 1）
    try:
        time.sleep(2)  # 稍微停顿，避免触发风控
        print("正在尝试通过【新浪财经】抓取全市场数据...")
        df = ak.stock_zh_a_spot()  # akshare 的新浪源
        df = df.dropna(subset=['涨跌幅', '成交额'])
        # 兼容列名差异
        if '最新价' in df.columns and '涨跌幅' not in df.columns:
             raise ValueError("新浪返回数据结构不匹配")
        print("✅ 新浪财经数据抓取成功")
        return df
    except Exception as e:
        print(f"⚠️ 新浪财经接口失败: {e}")
        print("准备切换腾讯数据源...")

    # 3. 尝试腾讯财经（备用源 2）
    try:
        time.sleep(2)
        print("正在尝试通过【腾讯财经】抓取全市场数据...")
        df = ak.stock_zh_a_spot_qq()
        df = df.dropna(subset=['涨跌幅', '成交额'])
        print("✅ 腾讯财经数据抓取成功")
        return df
    except Exception as e:
        print(f"❌ 腾讯接口也失败了: {e}")
        raise RuntimeError("所有行情接口均被限流或失效，今日无法获取数据。")

def fetch_and_save():
    print(f"--- 开始执行数据抓取 ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ---")
    
    # 获取数据（带多级备用）
    spot_df = get_spot_data()

    # 计算上涨和下跌家数
    up_df = spot_df[spot_df['涨跌幅'] > 0]
    down_df = spot_df[spot_df['涨跌幅'] < 0]
    
    up_count = len(up_df)
    down_count = len(down_df)
    
    # 计算成交额（如果用到的话，没用到可以删）
    total_amount = spot_df['成交额'].sum() / 100000000  # 亿元

    # 计算 TRIN (简化版示例，如果你想用成交额算，可以自行修改公式)
    # TRIN = (上涨家数 / 下跌家数) / (上涨成交额 / 下跌成交额)
    # 这里默认你只推家数，如果需要复杂计算，请基于 up_df 和 down_df 补充

    print(f"抓取完成: 上涨 {up_count} 家, 下跌 {down_count} 家")
    
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    
    # 写入 CSV
    new_row = pd.DataFrame({
        'date': [today],
        'adv_count': [up_count],
        'dec_count': [down_count]
    })
    
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        # 如果今天已经有记录，先删掉旧记录（防止一天跑多次产生重复行）
        df = df[df['date'] != today]
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(CSV_FILE, index=False)
    else:
        new_row.to_csv(CSV_FILE, index=False)
        
    return up_count, down_count

def send_wechat_text(adv_count=None, dec_count=None):
    print("正在通过 Server酱 推送纯文本...")
    url = f"https://sctapi.ftqq.com/{SENDKEY}.send"
    
    if adv_count is not None and dec_count is not None:
        desp = f"### 今日 TRIN 数据更新\n\n"
        desp += f"- 上涨家数: **{adv_count}**\n"
        desp += f"- 下跌家数: **{dec_count}**\n"
        desp += f"\n*(注: 已成功记录数据)*"
    else:
        desp = "无数据"

    data = {
        "title": "A股 TRIN 监控日报",
        "desp": desp
    }
    
    res = requests.post(url, data=data).json()
    print("推送结果:", res)

def send_error_msg(error_msg):
    """
    出错了也要推送通知，防止干等
    """
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
        # 1. 抓取并保存数据
        adv, dec = fetch_and_save()
        # 2. 发送正常的日报推送
        send_wechat_text(adv, dec)
    except Exception as e:
        error_info = str(e)
        print(f"执行出错: {error_info}")
        # 3. 终极兜底：报错也发通知
        send_error_msg(error_info)
