#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CryptoLake · P5 流失预测模型
==========================
目标: 预测用户是否会流失(最近 30 天无交易 = 流失)。
特征工程 -> 训练逻辑回归 + 随机森林 -> 评估 AUC -> 解释特征重要性。

用法: python ml/churn_model.py
"""
import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score, classification_report

DB_URL = "mysql+pymysql://root:root@127.0.0.1:3306/cryptolake?charset=utf8mb4"
AS_OF = "2026-07-01"       # 观测点
engine = create_engine(DB_URL)


def build_features():
    """从交易/登录/充提聚合出用户级特征。"""
    sql = f"""
    SELECT
        u.user_id, u.kyc_level, u.vip_level, u.reg_channel,
        DATEDIFF('{AS_OF}', u.reg_time)                    AS account_age_days,
        COALESCE(t.trades, 0)                              AS trades,
        COALESCE(t.gmv, 0)                                 AS gmv,
        COALESCE(t.fee, 0)                                 AS fee,
        COALESCE(t.active_days, 0)                         AS active_days,
        COALESCE(DATEDIFF('{AS_OF}', t.last_trade), 999)   AS days_since_last_trade,
        COALESCE(l.logins, 0)                              AS logins,
        COALESCE(d.deposit_cnt, 0)                         AS deposit_cnt,
        COALESCE(d.deposit_usd, 0)                         AS deposit_usd
    FROM dim_user u
    LEFT JOIN (
        SELECT user_id, COUNT(*) trades, SUM(amount) gmv, SUM(fee) fee,
               COUNT(DISTINCT DATE(ts)) active_days, MAX(DATE(ts)) last_trade
        FROM fact_trade GROUP BY user_id
    ) t ON t.user_id = u.user_id
    LEFT JOIN (SELECT user_id, COUNT(*) logins FROM fact_login GROUP BY user_id) l
        ON l.user_id = u.user_id
    LEFT JOIN (
        SELECT user_id, COUNT(*) deposit_cnt, SUM(amount_usd) deposit_usd
        FROM fact_deposit_withdraw WHERE direction='DEPOSIT' GROUP BY user_id
    ) d ON d.user_id = u.user_id
    """
    df = pd.read_sql(sql, engine)
    # 标签: 最近 30 天无交易 = 流失(1)
    df["churned"] = (df["days_since_last_trade"] > 30).astype(int)
    # days_since_last_trade 与标签强相关(泄露), 建模时剔除
    df = df.drop(columns=["days_since_last_trade"])
    # 渠道 one-hot
    df = pd.get_dummies(df, columns=["reg_channel"], prefix="ch")
    return df


def main():
    df = build_features()
    print(f"样本 {len(df)}, 流失率 {df['churned'].mean()*100:.1f}%")

    y = df["churned"]
    X = df.drop(columns=["user_id", "churned"]).astype(float)
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y)

    # --- 逻辑回归(需标准化) ---
    sc = StandardScaler().fit(X_tr)
    lr = LogisticRegression(max_iter=1000, class_weight="balanced")
    lr.fit(sc.transform(X_tr), y_tr)
    auc_lr = roc_auc_score(y_te, lr.predict_proba(sc.transform(X_te))[:, 1])

    # --- 随机森林 ---
    rf = RandomForestClassifier(n_estimators=200, max_depth=8,
                                class_weight="balanced", random_state=42)
    rf.fit(X_tr, y_tr)
    proba = rf.predict_proba(X_te)[:, 1]
    auc_rf = roc_auc_score(y_te, proba)

    print(f"\nAUC  逻辑回归 = {auc_lr:.3f}   随机森林 = {auc_rf:.3f}")
    print("\n随机森林分类报告(阈值 0.5):")
    print(classification_report(y_te, (proba > 0.5).astype(int),
                                target_names=["留存", "流失"]))

    imp = pd.Series(rf.feature_importances_, index=X.columns).sort_values(ascending=False)
    print("Top 特征重要性:")
    for k, v in imp.head(8).items():
        print(f"  {k:<22} {v:.3f}")

    print("\n业务用法: 对预测流失概率高、且历史手续费高的用户, 优先发召回券/客户经理跟进。")


if __name__ == "__main__":
    main()
