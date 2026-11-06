import akshare as ak
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime
import os
import requests
import base64
import io

# ================= 配置区 =================
# ⚠️ 注意：下一步要把这里的文字换成你的 SendKey
SENDKEY = "SCT463844TNcz5U47QQNahk4owcCxxRGdV" 
# ==========================================

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False 

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
        new_row.to_csv(CSV_FILE, index=False)
        print(f"首次创建文件，已保存 {today} 数据。")

def draw_chart():
    if not os.path.exists(CSV_FILE):
        return None, 0
    
    df = pd.read_csv(CSV_FILE)
    df['TRIN_Raw'] = (df['adv_count'] * df['dec_vol']) / (df['dec_count'].clip(lower=1) * df['adv_vol'].clip(lower=1))
    df['TRIN_Smooth'] = df['TRIN_Raw'].ewm(span=5, adjust=False).mean()
    
    plot_df = df.tail(15).copy()
    plot_df['Bar_Height'] = plot_df['adv_vol'] / 1e8 
    
    fig, ax1 = plt.subplots(figsize=(10, 5), facecolor='#1e1e1e')
    ax1.set_facecolor('#1e1e1e')
    
    bars = ax1.bar(plot_df['date'], plot_df['Bar_Height'], color='#d32f2f', width=0.4, alpha=0.6)
    ax1.set_yticks([])
    ax1.set_ylim(0, plot_df['Bar_Height'].max() * 1.5 if not plot_df.empty else 100)
    
    ax2 = ax1.twinx()
    ax2.set_facecolor('#1e1e1e')
    ax2.plot(plot_df['date'], plot_df['TRIN_Raw'], color='#3b82f6', marker='o', linewidth=2, label='TRIN (原始)')
    ax2.plot(plot_df['date'], plot_df['TRIN_Smooth'], color='#84cc16', marker='o', linewidth=2, linestyle='--', label='TRIN (平滑)')
    ax2.axhline(y=1.0, color='#eab308', linestyle='--', linewidth=1.5, label='多空分水岭 1.0')
    
    for i in range(len(plot_df)):
        row = plot_df.iloc[i]
        offset_y = 12 if row['TRIN_Raw'] > 1.0 else -18 
        ax2.annotate(f"{row['TRIN_Raw']:.2f}", (row['date'], row['TRIN_Raw']), 
                     textcoords="offset points", xytext=(0, offset_y), ha='center', 
                     color='#60a5fa', fontsize=10, fontweight='bold')
                     
    ax2.set_ylim(0, max(plot_df['TRIN_Raw'].max() * 1.3, 2.5))
    ax2.set_yticks([0, 0.5, 1.0, 1.5, 2.0])
    ax2.tick_params(axis='y', colors='white')
    ax1.tick_params(axis='x', colors='white')
    
    lines_1, labels_1 = ax1.get_legend_handles_labels()
    lines_2, labels_2 = ax2.get_legend_handles_labels()
    ax1.legend(lines_1 + lines_2, labels_1 + labels_2, loc='upper left', facecolor='#1e1e1e', edgecolor='gray')
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', facecolor='#1e1e1e')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    
    latest_trin = df['TRIN_Raw'].iloc[-1]
    return img_base64, latest_trin

def send_wechat_serverchan(img_base64, trin_val):
    print("正在通过 Server酱 推送到微信...")
    url = f"https://sctapi.ftqq.com/{SENDKEY}.send"
    
    desp = f"### 今日 TRIN 数据更新\n\n最新原始 TRIN: **{trin_val:.2f}**\n\n![TRIN图表](data:image/png;base64,{img_base64})"
    
    data = {
        "title": "A股 TRIN 监控日报",
        "desp": desp
    }
    res = requests.post(url, data=data).json()
    print("推送结果:", res)

if __name__ == "__main__":
    try:
        fetch_and_save()
        img, trin = draw_chart()
        if img:
            send_wechat_serverchan(img, trin)
    except Exception as e:
        print(f"执行出错: {e}")
