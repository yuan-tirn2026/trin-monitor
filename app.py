import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="TRIN市场涨跌指标", layout="wide")
st.title("📊 A股TRIN涨跌指标监控")

df = pd.read_csv("trin_history.csv")
df["date"] = pd.to_datetime(df["date"], format="%m-%d")
df["trin"] = (df["adv_count"] / df["dec_count"]) / (df["adv_vol"] / df["dec_vol"])

st.subheader("TRIN 曲线")
st.line_chart(df, x="date", y="trin")

st.subheader("原始数据")
st.dataframe(df, use_container_width=True)

st.markdown("""
> TRIN = (上涨家数/下跌家数) ÷ (上涨成交额/下跌成交额)
> TRIN>1：空头占优；TRIN<1：多头占优
""")
