import akshare as ak
import pandas as pd
import datetime
import os
import requests

# ================= 配置区 =================
# 把下面的字替换成你的 Server酱 SendKey
SENDKEY = "SCT463844TNcz5U47QQNahk4owcCxxRGdV" 
# ==========================================

CSV_FILE = "trin_history.csv"

def fetch_and_save():
    print("正在抓取全市场数据...")
    spot_df = ak.stock_zh_a_spot_em().dropna(subset=['涨跌幅', '成交额'])
    up_df = spot_df[spot_df['涨跌幅'] > 0]
    down_df = spot_df[spot_df['涨跌幅'] < 0]
    
    today = datetime.datetime.now().strftime('%m-%d')
    
    new_row = pd.DataFrame({
        'date': [today],
        'adv_count': [len(up_df)],
        'dec_count': [len(down_df)],
        'adv_vol': [up_df['成交额'].sum()],
        'dec_vol': [down_df['成交额'].sum()]
    })
    
    if os.path.exists(CSV_FILE):
        history = pd.read_csv(CSV_FILE)
        if today not in history['date'].values:
            history = pd.concat([history, new_row], ignore_index=True)
            history.to_csv(CSV_FILE, index=False)
            print(f"成功追加 {today} 数据！")
        else:
            print(f"{today} 数据已存在，跳过抓取。")
    else:
        new_row.to_csv(CSV_FILE, index=False)
        print(f"首次创建文件，已保存 {today} 数据。")

def send_wechat_text():
    print("正在通过 Server酱 推送纯文本...")
    
    if not os.path.exists(CSV_FILE):
        print("数据文件不存在")
        return
        
    df = pd.read_csv(CSV_FILE)
    # 计算最新的TRIN
    df['TRIN_Raw'] = (df['adv_count'] * df['dec_vol']) / (df['dec_count'].clip(lower=1) * df['adv_vol'].clip(lower=1))
    
    latest = df.iloc[-1]
    trin_val = latest['TRIN_Raw']
    adv_count = latest['adv_count']
    dec_count = latest['dec_count']
    
    url = f"https://sctapi.ftqq.com/{SENDKEY}.send"
    
    # 构造纯文字内容
    desp = f"### 今日 TRIN 数据更新\n\n"
    desp += f"- 最新原始 TRIN: **{trin_val:.2f}**\n"
    desp += f"- 上涨家数: {adv_count}\n"
    desp += f"- 下跌家数: {dec_count}\n"
    desp += f"\n*(注: 已成功记录数据，因云端服务器限制，暂改为纯文本推送)*"
    
    data = {
        "title": "A股 TRIN 监控日报",
        "desp": desp
    }
    res = requests.post(url, data=data).json()
    print("推送结果:", res)

if __name__ == "__main__":
    try:
        fetch_and_save()
        send_wechat_text()
    except Exception as e:
        print(f"执行出错: {e}")
