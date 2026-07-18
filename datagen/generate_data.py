#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CryptoLake · 造数脚本
====================
按"贴近真实"的分布生成交易平台数据, 写入 MySQL(cryptolake 库)。

设计要点(面试可讲):
  * 交易频次   -> 泊松分布 (每个用户 lambda 不同)
  * 鲸鱼/散户  -> 幂律思想: 少数鲸鱼贡献大部分成交额与手续费
  * 币价       -> 随机游走生成日 K 线, 成交价在当日高低区间内浮动
  * 手续费     -> amount * fee_rate, fee_rate 随 VIP 等级递减
  * 故意埋点   -> 一部分用户是"流失用户"(只在注册后前两周活跃)
                 一部分账户是"异常账户"(交易额远超同层), 供后续风控/建模

先跑 sql/01_schema.sql 建好库表, 再跑本脚本。
用法:
  pip install -r requirements.txt
  python datagen/generate_data.py                 # 默认规模
  python datagen/generate_data.py --users 20000   # 放大规模
"""
import argparse
import datetime as dt
import numpy as np
import pandas as pd
from sqlalchemy import create_engine

# ------------------------------------------------------------------
# 配置(按需改这里)
# ------------------------------------------------------------------
DB_URL = "mysql+pymysql://root:root@127.0.0.1:3306/cryptolake?charset=utf8mb4"
SEED = 42
np.random.seed(SEED)

# 资产: symbol, 名称, 类别, 起始价格
ASSETS = [
    ("BTC",  "Bitcoin",      "major",      42000.0),
    ("ETH",  "Ethereum",     "major",      2300.0),
    ("BNB",  "BNB",          "major",      310.0),
    ("SOL",  "Solana",       "altcoin",    98.0),
    ("XRP",  "Ripple",       "altcoin",    0.52),
    ("DOGE", "Dogecoin",     "altcoin",    0.08),
    ("ADA",  "Cardano",      "altcoin",    0.45),
    ("USDT", "Tether",       "stablecoin", 1.0),
    ("USDC", "USD Coin",     "stablecoin", 1.0),
]
# 主流币被交易得更多 -> 权重
ASSET_WEIGHT = [0.30, 0.22, 0.10, 0.12, 0.08, 0.06, 0.05, 0.04, 0.03]

COUNTRIES = ["US", "SG", "JP", "KR", "GB", "DE", "BR", "IN", "TR", "NG"]
COUNTRY_W = [0.20, 0.10, 0.12, 0.10, 0.08, 0.07, 0.09, 0.10, 0.08, 0.06]

CHANNELS = ["organic", "referral", "ads_google", "ads_twitter", "kol"]
CHANNEL_W = [0.35, 0.20, 0.18, 0.15, 0.12]

# VIP 等级 -> 手续费率(挂单方近似, 越高越低)
VIP_FEE_RATE = {0: 0.0010, 1: 0.0009, 2: 0.0008, 3: 0.0007, 4: 0.0005, 5: 0.0003}


def build_dates(start, end):
    days = pd.date_range(start, end, freq="D")
    rows = []
    for d in days:
        iso = d.isocalendar()
        rows.append((d.date(), d.year, d.month, d.day, int(iso.week),
                     (d.month - 1) // 3 + 1, 1 if d.weekday() >= 5 else 0))
    return pd.DataFrame(rows, columns=["date_id", "year", "month", "day",
                                       "week", "quarter", "is_weekend"])


def build_klines(asset_df, dates):
    """每个资产按随机游走生成日 K 线。"""
    rows = []
    kid = 1
    day_list = list(dates["date_id"])
    for _, a in asset_df.iterrows():
        price = float(a["start_price"])
        # 稳定币波动极小
        vol = 0.002 if a["category"] == "stablecoin" else 0.035
        for d in day_list:
            ret = np.random.normal(0, vol)
            close = max(price * (1 + ret), 1e-6)
            hi = max(price, close) * (1 + abs(np.random.normal(0, vol / 2)))
            lo = min(price, close) * (1 - abs(np.random.normal(0, vol / 2)))
            volume = abs(np.random.normal(1_000_000, 300_000))
            rows.append((kid, int(a["asset_id"]), d, round(price, 8),
                         round(hi, 8), round(lo, 8), round(close, 8), round(volume, 4)))
            price = close
            kid += 1
    return pd.DataFrame(rows, columns=["id", "asset_id", "kline_date",
                                       "open", "high", "low", "close", "volume"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--users", type=int, default=5000, help="用户数(默认 5000)")
    ap.add_argument("--days", type=int, default=365, help="数据跨度天数(默认 365)")
    ap.add_argument("--db", type=str, default=DB_URL)
    args = ap.parse_args()

    engine = create_engine(args.db)
    end_date = dt.date(2026, 7, 1)
    start_date = end_date - dt.timedelta(days=args.days)
    print(f"▶ 生成范围 {start_date} ~ {end_date}, 用户 {args.users}")

    # ---------- dim_date ----------
    dates = build_dates(start_date, end_date)
    dates.to_sql("dim_date", engine, if_exists="append", index=False)
    print(f"  dim_date        {len(dates):>8} 行")

    # ---------- dim_asset ----------
    asset_df = pd.DataFrame(
        [(i + 1, s, n, c, p) for i, (s, n, c, p) in enumerate(ASSETS)],
        columns=["asset_id", "symbol", "asset_name", "category", "start_price"])
    asset_df[["asset_id", "symbol", "asset_name", "category"]].to_sql(
        "dim_asset", engine, if_exists="append", index=False)
    print(f"  dim_asset       {len(asset_df):>8} 行")
    # 可交易的基础币(排除稳定币做基础币)
    tradable = asset_df[asset_df["category"] != "stablecoin"].reset_index(drop=True)
    trade_w = np.array(ASSET_WEIGHT[:len(tradable)])
    trade_w = trade_w / trade_w.sum()

    # ---------- fact_kline ----------
    klines = build_klines(asset_df, dates)
    klines.to_sql("fact_kline", engine, if_exists="append", index=False, chunksize=5000)
    print(f"  fact_kline      {len(klines):>8} 行")
    # 收盘价查询字典: (asset_id, date) -> close
    close_map = {(r.asset_id, r.kline_date): float(r.close) for r in klines.itertuples()}
    kline_dates = list(dates["date_id"])

    # ---------- dim_user ----------
    n = args.users
    reg_offsets = np.random.randint(0, args.days, size=n)  # 注册在区间内均匀分布
    # 15% 鲸鱼倾向, 20% 流失用户, 2% 异常账户
    is_whale = np.random.random(n) < 0.15
    is_churn = np.random.random(n) < 0.20
    is_anomaly = np.random.random(n) < 0.02
    # VIP: 大多数 0 级(幂律), 鲸鱼更容易高 VIP
    vip = np.random.choice([0, 1, 2, 3, 4, 5], size=n,
                           p=[0.55, 0.20, 0.12, 0.07, 0.04, 0.02])
    vip = np.where(is_whale & (vip < 2), np.random.randint(2, 6, size=n), vip)

    users = []
    for i in range(n):
        uid = i + 1
        reg = dt.datetime.combine(start_date + dt.timedelta(days=int(reg_offsets[i])),
                                  dt.time(int(np.random.randint(0, 24)),
                                          int(np.random.randint(0, 60))))
        channel = np.random.choice(CHANNELS, p=CHANNEL_W)
        referrer = int(np.random.randint(1, max(2, uid))) if channel == "referral" and uid > 1 else None
        kyc = int(np.random.choice([0, 1, 2], p=[0.25, 0.45, 0.30]))
        users.append((uid, reg, np.random.choice(COUNTRIES, p=COUNTRY_W),
                      kyc, channel, referrer, int(vip[i])))
    user_df = pd.DataFrame(users, columns=["user_id", "reg_time", "country",
                                           "kyc_level", "reg_channel",
                                           "referrer_id", "vip_level"])
    user_df.to_sql("dim_user", engine, if_exists="append", index=False, chunksize=2000)
    print(f"  dim_user        {n:>8} 行")

    # ---------- 生成交易 / 挂单 / 充提 / 登录 ----------
    trades, orders, dw, logins = [], [], [], []
    tid = oid = did = lid = 1
    for i in range(n):
        uid = i + 1
        reg = user_df.at[i, "reg_time"]
        reg_d = reg.date()
        # 用户活跃窗口
        if is_churn[i]:
            active_days = 14                      # 流失用户只活跃两周
        else:
            active_days = (end_date - reg_d).days
        active_days = max(1, active_days)

        # 交易频次: 泊松. 鲸鱼 lambda 高
        base_lambda = 3.0 if is_whale[i] else 0.6
        n_trades = np.random.poisson(base_lambda * active_days / 30.0 * 3)
        if is_anomaly[i]:
            n_trades = int(n_trades * 5) + 20     # 异常账户交易极多

        fee_rate = VIP_FEE_RATE[int(vip[i])]

        # 每个用户一次初始充值
        dep_amt = float(abs(np.random.lognormal(7 if is_whale[i] else 5, 1.0)))
        dw.append((did, uid, "DEPOSIT", 8, round(dep_amt, 4),   # asset_id 8 = USDT
                   reg + dt.timedelta(hours=int(np.random.randint(1, 48)))))
        did += 1

        for _ in range(int(n_trades)):
            offset = int(np.random.randint(0, active_days + 1))
            tdate = reg_d + dt.timedelta(days=offset)
            if tdate > end_date:
                continue
            ai = int(np.random.choice(tradable.index, p=trade_w))
            asset_id = int(tradable.at[ai, "asset_id"])
            symbol = f"{tradable.at[ai, 'symbol']}/USDT"
            close = close_map.get((asset_id, tdate)) or float(tradable.at[ai, "start_price"])
            price = max(close * (1 + np.random.normal(0, 0.01)), 1e-6)
            # 鲸鱼/异常下单量更大
            usd = abs(np.random.lognormal(9 if (is_whale[i] or is_anomaly[i]) else 5.5, 1.1))
            qty = usd / price
            amount = qty * price
            fee = amount * fee_rate
            side = "BUY" if np.random.random() < 0.5 else "SELL"
            ts = dt.datetime.combine(tdate, dt.time(int(np.random.randint(0, 24)),
                                                    int(np.random.randint(0, 60)),
                                                    int(np.random.randint(0, 60))))
            trades.append((tid, uid, asset_id, symbol, side,
                           round(price, 8), round(qty, 8), round(amount, 8),
                           round(fee, 8), ts))
            # 对应一条 FILLED 挂单
            orders.append((oid, uid, asset_id, side, round(price, 8), round(qty, 8),
                           "FILLED", ts, ts))
            oid += 1
            tid += 1

        # 额外的撤单/未成交挂单(约成交量的 30%)
        n_cancel = np.random.poisson(max(0.3 * n_trades, 0.5))
        for _ in range(int(n_cancel)):
            offset = int(np.random.randint(0, active_days + 1))
            odate = reg_d + dt.timedelta(days=offset)
            if odate > end_date:
                continue
            ai = int(np.random.choice(tradable.index, p=trade_w))
            asset_id = int(tradable.at[ai, "asset_id"])
            close = close_map.get((asset_id, odate)) or float(tradable.at[ai, "start_price"])
            price = max(close * (1 + np.random.normal(0, 0.03)), 1e-6)
            usd = abs(np.random.lognormal(5.5, 1.0))
            ct = dt.datetime.combine(odate, dt.time(int(np.random.randint(0, 24)),
                                                    int(np.random.randint(0, 60))))
            status = "CANCELED" if np.random.random() < 0.8 else "OPEN"
            orders.append((oid, uid, asset_id,
                           "BUY" if np.random.random() < 0.5 else "SELL",
                           round(price, 8), round(usd / price, 8), status, ct,
                           ct + dt.timedelta(minutes=int(np.random.randint(1, 120)))))
            oid += 1

        # 提现(部分用户)
        if np.random.random() < 0.4:
            wdate = reg_d + dt.timedelta(days=int(np.random.randint(0, active_days + 1)))
            if wdate <= end_date:
                dw.append((did, uid, "WITHDRAW", 8,
                           round(abs(np.random.lognormal(5, 1.0)), 4),
                           dt.datetime.combine(wdate, dt.time(int(np.random.randint(0, 24)), 0))))
                did += 1

        # 登录: 活跃期内随机若干天
        n_login = np.random.poisson(max(active_days / 7.0, 1))
        for _ in range(int(n_login)):
            ld = reg_d + dt.timedelta(days=int(np.random.randint(0, active_days + 1)))
            if ld > end_date:
                continue
            logins.append((lid, uid,
                           dt.datetime.combine(ld, dt.time(int(np.random.randint(0, 24)),
                                                           int(np.random.randint(0, 60)))),
                           np.random.choice(["web", "ios", "android"], p=[0.4, 0.35, 0.25])))
            lid += 1

    def dump(rows, cols, table):
        if not rows:
            return
        df = pd.DataFrame(rows, columns=cols)
        df.to_sql(table, engine, if_exists="append", index=False, chunksize=5000)
        print(f"  {table:<15} {len(df):>8} 行")

    dump(trades, ["trade_id", "user_id", "base_asset_id", "symbol", "side",
                  "price", "qty", "amount", "fee", "ts"], "fact_trade")
    dump(orders, ["order_id", "user_id", "base_asset_id", "side", "price", "qty",
                  "status", "create_ts", "update_ts"], "fact_order")
    dump(dw, ["id", "user_id", "direction", "asset_id", "amount_usd", "ts"],
         "fact_deposit_withdraw")
    dump(logins, ["id", "user_id", "login_ts", "device"], "fact_login")

    print("✔ 全部数据写入完成")


if __name__ == "__main__":
    main()
