#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CryptoLake · P3 Python 分析
==========================
用 pandas 复现并深化 SQL 分析, 用 matplotlib 出图, 并做一个 A/B 测试。
产出: analysis/output/ 下若干 PNG + 控制台结论。

用法: python analysis/analysis.py
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats
from sqlalchemy import create_engine

DB_URL = "mysql+pymysql://root:root@127.0.0.1:3306/cryptolake?charset=utf8mb4"
OUT = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUT, exist_ok=True)
engine = create_engine(DB_URL)
plt.rcParams["axes.unicode_minus"] = False


def q(sql):
    return pd.read_sql(sql, engine)


# ---------------------------------------------------------------
# 1. DAU 趋势
# ---------------------------------------------------------------
def dau_trend():
    df = q("SELECT DATE(ts) d, COUNT(DISTINCT user_id) dau "
           "FROM fact_trade GROUP BY DATE(ts) ORDER BY d")
    df["d"] = pd.to_datetime(df["d"])
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(df["d"], df["dau"], color="#e8b341", lw=1.6)
    ax.fill_between(df["d"], df["dau"], color="#e8b341", alpha=0.12)
    ax.set_title("Daily Active Traders (DAU)")
    ax.set_ylabel("DAU"); fig.autofmt_xdate()
    fig.tight_layout(); fig.savefig(f"{OUT}/01_dau_trend.png", dpi=120)
    print(f"[DAU] 均值 {df['dau'].mean():.0f}, 峰值 {df['dau'].max()}")


# ---------------------------------------------------------------
# 2. 手续费收入按币种(Top)
# ---------------------------------------------------------------
def fee_by_asset():
    df = q("""SELECT a.symbol, SUM(t.fee) fee
              FROM fact_trade t JOIN dim_asset a ON a.asset_id=t.base_asset_id
              GROUP BY a.symbol ORDER BY fee DESC""")
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(df["symbol"], df["fee"], color="#2bb596")
    ax.set_title("Fee Revenue by Asset (USDT)")
    fig.tight_layout(); fig.savefig(f"{OUT}/02_fee_by_asset.png", dpi=120)
    top = df.iloc[0]
    print(f"[营收] 手续费第一大来源: {top['symbol']} = {top['fee']:.0f} USDT "
          f"({100*top['fee']/df['fee'].sum():.1f}%)")


# ---------------------------------------------------------------
# 3. 留存曲线(注册后 0..14 天)
# ---------------------------------------------------------------
def retention_curve():
    df = q("""
        WITH fd AS (SELECT user_id, DATE(reg_time) c FROM dim_user),
             act AS (SELECT DISTINCT user_id, DATE(ts) a FROM fact_trade)
        SELECT DATEDIFF(act.a, fd.c) day_n, COUNT(DISTINCT fd.user_id) cnt
        FROM fd LEFT JOIN act ON act.user_id=fd.user_id
        WHERE DATEDIFF(act.a, fd.c) BETWEEN 0 AND 14
        GROUP BY day_n ORDER BY day_n""")
    base = q("SELECT COUNT(*) n FROM dim_user")["n"][0]
    df["rate"] = 100 * df["cnt"] / base
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(df["day_n"], df["rate"], marker="o", color="#e8b341")
    ax.set_title("Retention Curve (Day 0-14)")
    ax.set_xlabel("Days since registration"); ax.set_ylabel("% active")
    fig.tight_layout(); fig.savefig(f"{OUT}/03_retention.png", dpi=120)
    d7 = df.loc[df["day_n"] == 7, "rate"]
    print(f"[留存] 7日留存 ≈ {d7.values[0]:.1f}%" if len(d7) else "[留存] 无 D7 数据")


# ---------------------------------------------------------------
# 4. A/B 测试: "新手礼包" 是否提升 7 日留存
#    这里用模拟分组演示假设检验流程(实验/对照各半)。
#    实际项目里 group 应来自埋点表; 此处用 user_id 奇偶模拟随机分流。
# ---------------------------------------------------------------
def ab_test():
    users = q("SELECT user_id FROM dim_user")
    act = q("""WITH fd AS (SELECT user_id, DATE(reg_time) c FROM dim_user),
                    a AS (SELECT DISTINCT user_id, DATE(ts) d FROM fact_trade)
               SELECT fd.user_id,
                      MAX(CASE WHEN DATEDIFF(a.d,fd.c)=7 THEN 1 ELSE 0 END) d7
               FROM fd LEFT JOIN a ON a.user_id=fd.user_id
               GROUP BY fd.user_id""")
    df = users.merge(act, on="user_id", how="left").fillna({"d7": 0})
    # 随机分流(种子固定): B 组模拟收到礼包, 留存被"提升"
    rng = np.random.default_rng(7)
    df["group"] = rng.integers(0, 2, len(df))      # 0=对照 A, 1=实验 B
    # 模拟礼包效果: 给 B 组一部分未留存用户翻转为留存(教学演示)
    flip = (df["group"] == 1) & (df["d7"] == 0) & (rng.random(len(df)) < 0.05)
    df.loc[flip, "d7"] = 1

    a = df[df["group"] == 0]["d7"]
    b = df[df["group"] == 1]["d7"]
    # 两比例 z 检验
    n1, n2 = len(a), len(b)
    p1, p2 = a.mean(), b.mean()
    p_pool = (a.sum() + b.sum()) / (n1 + n2)
    se = np.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
    z = (p2 - p1) / se
    pval = 2 * (1 - stats.norm.cdf(abs(z)))
    print("\n[A/B 测试] 新手礼包 → 7 日留存")
    print(f"  对照 A: {p1*100:.2f}%  (n={n1})")
    print(f"  实验 B: {p2*100:.2f}%  (n={n2})")
    print(f"  提升 {(p2-p1)*100:+.2f}pp,  z={z:.2f},  p={pval:.4f}")
    print("  结论: " + ("差异显著(p<0.05), 建议全量上线 ✔"
                        if pval < 0.05 else "差异不显著, 需加大样本或迭代方案 ✘"))

    fig, ax = plt.subplots(figsize=(5, 4))
    ax.bar(["A 对照", "B 实验"], [p1 * 100, p2 * 100],
           color=["#8a8f9c", "#2bb596"])
    ax.set_title(f"7-day retention  (p={pval:.3f})")
    ax.set_ylabel("%")
    fig.tight_layout(); fig.savefig(f"{OUT}/04_ab_test.png", dpi=120)


if __name__ == "__main__":
    print("=== CryptoLake Python 分析 ===")
    dau_trend()
    fee_by_asset()
    retention_curve()
    ab_test()
    print(f"\n✔ 图表已输出到 {OUT}/")
