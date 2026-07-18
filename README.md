# CryptoLake · 币安式加密交易平台数据仓库与分析

> 一个数据分析师作品集项目:自建交易平台数据仓库(MySQL),扮演它的数据分析师,
> 用 SQL / Python / 大数据 / BI / 机器学习 回答真实业务问题。
> 配套 18 个月学习路线图见 [`roadmap.html`](roadmap.html)(浏览器打开,**每个阶段都配了结果产物效果图**,照着对照就知道目标长什么样),简历模板见 [`resume.html`](resume.html)。

![stack](https://img.shields.io/badge/stack-MySQL·Python·Spark·dbt·Airflow·sklearn-e8b341)

---

## 🎯 这个项目在解决什么

加密交易平台靠**交易手续费**赚钱。作为它的数据分析师,你要回答:

- 新用户第 7 天还回来吗?(留存)
- 哪个渠道来的用户最能贡献手续费?(渠道 ROI)
- 大户(鲸鱼)和散户行为差在哪?(RFM 分层)
- 手续费收入靠哪些币种 / VIP 等级支撑?(营收拆解)
- 哪些账户交易行为异常?(风控)
- 能不能提前预测谁要流失?(机器学习)

没有真实数据,就用 Python 按**真实分布**(泊松、幂律、随机游走)造一套。

---

## 📁 项目结构

```
CryptoLake/
├── README.md                    ← 你在这
├── roadmap.html                 18 个月学习路线图(浏览器打开)
├── resume.html                  数据分析师简历模板(可导出 PDF)
├── requirements.txt             Python 依赖
├── sql/
│   ├── 01_schema.sql            建库 + 星型模型 8 张表
│   └── 02_analysis.sql          核心业务分析(漏斗/留存/RFM/营收/渠道/风控)
├── datagen/
│   └── generate_data.py         造数(真实分布 + 埋点流失/异常用户)
├── analysis/
│   └── analysis.py              pandas 分析 + 可视化 + A/B 测试
├── ml/
│   └── churn_model.py           流失预测(逻辑回归 + 随机森林 + 特征重要性)
├── warehouse/                   dbt 分层数仓 ODS→DWD→DWS→ADS
│   ├── dbt_project.yml
│   ├── profiles.example.yml
│   └── models/{ods,dwd,dws,ads}/*.sql
├── spark/
│   └── spark_analysis.py        Spark SQL 版本(大数据量)
├── airflow/
│   └── cryptolake_dag.py        Airflow 每日调度 DAG
└── docs/                        全套本地环境搭建步骤
    ├── 00_环境搭建_MySQL.md
    ├── 01_环境搭建_Python.md
    ├── 02_环境搭建_Hadoop_Spark.md
    ├── 03_环境搭建_dbt_Airflow.md
    └── 04_环境搭建_Superset_BI.md
```

---

## 🚀 快速开始(最短路径,当天能跑通)

```bash
# 0. 前置:装好 MySQL 8.0+(见 docs/00)、Python 3.11+(见 docs/01)

cd /Users/tommy/CryptoLake
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1. 建库建表
mysql -u root -p < sql/01_schema.sql

# 2. 造数据(默认 5000 用户,几分钟)
python datagen/generate_data.py

# 3. 跑业务分析 SQL(或在 DBeaver 里逐段跑,更直观)
mysql -u root -p cryptolake < sql/02_analysis.sql

# 4. Python 分析 + 出图 + A/B 测试
python analysis/analysis.py        # 图在 analysis/output/

# 5. 流失预测模型
python ml/churn_model.py
```

进阶(大数据 / 工程化)见 `docs/02`、`docs/03`、`docs/04`。

---

## 🗺️ 对应 18 个月学习路线

| 阶段 | 月份 | 做这个项目的哪部分 | 交付物 |
|---|---|---|---|
| P1 | 1–3 | `sql/01_schema.sql` + `datagen/` | 数仓 + 造数脚本 |
| P2 | 4–6 | `sql/02_analysis.sql` | 业务分析报告 |
| P3 | 7–9 | `analysis/analysis.py` | Jupyter 分析 + A/B |
| P4 | 10–12 | `warehouse/`(dbt) + `spark/` + `airflow/` | 端到端数据管道 |
| P5 | 13–15 | `ml/churn_model.py` + `docs/04`(BI 看板) | 模型 + 看板 |
| P6 | 16–18 | 整理成 GitHub 仓库 + 下面的简历模板 | 简历 + 投递 |

---

## 📝 简历怎么写(P6)

照抄改数字(把 `[占位]` 换成你真跑出来的结果):

> **CryptoLake · 加密交易平台用户与营收分析** (个人项目)
>
> - 独立设计并搭建交易平台数据仓库(MySQL 星型模型 8 表),用 Python 按真实分布模拟 `[千万]` 级交易数据。
> - 运用窗口函数 / CTE 完成 AARRR 漏斗、留存 cohort、RFM 分层,定位贡献 `[80%]` 手续费的核心用户群并给出分层运营建议。
> - 用 pandas 复现分析并设计 A/B 测试,通过假设检验验证运营策略对 7 日留存的提升具统计显著性(p `[<0.05]`)。
> - 基于 dbt 构建 ODS→DWD→DWS→ADS 分层数仓 + Airflow 调度,搭建 Superset 运营看板,训练流失预测模型(AUC `[0.8x]`)。

**诚信红线**:简历每一条面试都会被追问。这个项目的价值就是**你真做过,答得上"为什么这么建模、这个数字怎么算的"**。别写没亲手做过的东西。

---

## 🔧 配置说明

所有脚本默认连接:`mysql://root:root@127.0.0.1:3306/cryptolake`
改密码/端口的话,同步修改:
- `datagen/generate_data.py` 顶部 `DB_URL`
- `analysis/analysis.py`、`ml/churn_model.py` 顶部 `DB_URL`
- `spark/spark_analysis.py` 的 `JDBC` / `PROPS`
- `~/.dbt/profiles.yml`

---

## ✅ 每阶段自检

- 我能对着白板讲清这阶段做的东西吗?
- 它解决了什么业务问题?结论是什么?
- 代码上 GitHub 了吗?README 写了吗?
- 能用一句话让非技术的人听懂吗?

祝早日拿到 offer 🚀
