import akshare as ak
import pandas as pd
import numpy as np
import datetime
import os

CSV_FILE = "trin_history.csv"

def update_real_trin_data():
    print("正在抓取全市场数据...")
    try:
        spot_df = ak.stock_zh_a_spot_em()
        spot_df = spot_df.dropna(subset=['涨跌幅', '成交额'])
        up_df = spot_df[spot_df['涨跌幅']>0]
        down_df = spot_df[spot_df['涨跌幅']<0]

        adv_count = len(up_df)
        dec_count = len(down_df)
        adv_vol = up_df['成交额'].sum()
        dec_vol = down_df['成交额'].sum()

        today = datetime.datetime.now().strftime('%m-%d')
        new_data = pd.DataFrame({
            'date':[today],
            'adv_count':[adv_count],
            'dec_count':[dec_count],
            'adv_vol':[adv_vol],
            'dec_vol':[dec_vol]
        })

        if os.path.exists(CSV_FILE):
            history = pd.read_csv(CSV_FILE)
            if today in history['date'].values:
                print(f"{today}数据已存在，跳过")
            else:
                history = pd.concat([history, new_data], ignore_index=True)
                history.to_csv(CSV_FILE, index=False)
                print(f"追加 {today} 的数据")
        else:
            new_data.to_csv(CSV_FILE, index=False)
            print("首次创建csv")
    except Exception as e:
        print(f"抓取失败：{e}")

if __name__ == "__main__":
    update_real_trin_data()
