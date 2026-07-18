-- =============================================================
-- CryptoLake · 02_analysis.sql
-- 核心业务分析(P2 交付物). 每段都配"业务解读"注释。
-- 直接在 cryptolake 库里逐段运行, 边看结果边理解。
-- =============================================================
USE cryptolake;

-- =============================================================
-- A. 概览指标 —— 先摸清盘子有多大
-- =============================================================

-- A1. 总用户 / 总成交额 / 总手续费收入
SELECT
    (SELECT COUNT(*) FROM dim_user)                       AS total_users,
    (SELECT COUNT(*) FROM fact_trade)                     AS total_trades,
    ROUND((SELECT SUM(amount) FROM fact_trade), 2)        AS total_gmv_usdt,
    ROUND((SELECT SUM(fee)    FROM fact_trade), 2)        AS total_fee_revenue;

-- A2. 每日活跃用户 DAU(按当天有交易算)
SELECT DATE(ts) AS d, COUNT(DISTINCT user_id) AS dau
FROM fact_trade
GROUP BY DATE(ts)
ORDER BY d;

-- A3. 月活 MAU 与人均成交额
SELECT DATE_FORMAT(ts, '%Y-%m')                    AS ym,
       COUNT(DISTINCT user_id)                     AS mau,
       ROUND(SUM(amount) / COUNT(DISTINCT user_id), 2) AS gmv_per_user
FROM fact_trade
GROUP BY DATE_FORMAT(ts, '%Y-%m')
ORDER BY ym;

-- =============================================================
-- B. AARRR 漏斗 —— 注册 → 入金 → 首笔交易 → 复购
-- 业务解读: 哪一步流失最严重, 就是运营该优化的地方。
-- =============================================================
WITH funnel AS (
    SELECT
        u.user_id,
        MAX(CASE WHEN dw.direction = 'DEPOSIT' THEN 1 ELSE 0 END) AS has_deposit,
        MAX(CASE WHEN t.trade_id IS NOT NULL THEN 1 ELSE 0 END)   AS has_trade,
        COUNT(DISTINCT t.trade_id)                                AS trade_cnt
    FROM dim_user u
    LEFT JOIN fact_deposit_withdraw dw ON dw.user_id = u.user_id
    LEFT JOIN fact_trade t             ON t.user_id  = u.user_id
    GROUP BY u.user_id
)
SELECT
    COUNT(*)                                                   AS registered,
    SUM(has_deposit)                                           AS deposited,
    SUM(has_trade)                                             AS traded,
    SUM(CASE WHEN trade_cnt >= 2 THEN 1 ELSE 0 END)            AS repeat_traded,
    ROUND(100 * SUM(has_deposit) / COUNT(*), 1)                AS pct_deposit,
    ROUND(100 * SUM(has_trade)   / COUNT(*), 1)                AS pct_trade,
    ROUND(100 * SUM(CASE WHEN trade_cnt >= 2 THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_repeat
FROM funnel;

-- =============================================================
-- C. 留存 cohort —— 按注册周分组, 看第 1/7/30 天回访率
-- 业务解读: 留存曲线是产品健康度的核心指标。
-- =============================================================
WITH first_day AS (
    SELECT user_id, DATE(reg_time) AS cohort_day
    FROM dim_user
),
activity AS (
    SELECT DISTINCT user_id, DATE(ts) AS act_day
    FROM fact_trade
)
SELECT
    f.cohort_day,
    COUNT(DISTINCT f.user_id)                                            AS cohort_size,
    COUNT(DISTINCT CASE WHEN DATEDIFF(a.act_day, f.cohort_day) = 1
          THEN f.user_id END)                                            AS d1,
    COUNT(DISTINCT CASE WHEN DATEDIFF(a.act_day, f.cohort_day) = 7
          THEN f.user_id END)                                            AS d7,
    COUNT(DISTINCT CASE WHEN DATEDIFF(a.act_day, f.cohort_day) = 30
          THEN f.user_id END)                                            AS d30,
    ROUND(100 * COUNT(DISTINCT CASE WHEN DATEDIFF(a.act_day, f.cohort_day)=1
          THEN f.user_id END) / COUNT(DISTINCT f.user_id), 1)            AS d1_rate,
    ROUND(100 * COUNT(DISTINCT CASE WHEN DATEDIFF(a.act_day, f.cohort_day)=7
          THEN f.user_id END) / COUNT(DISTINCT f.user_id), 1)            AS d7_rate
FROM first_day f
LEFT JOIN activity a ON a.user_id = f.user_id
GROUP BY f.cohort_day
ORDER BY f.cohort_day;

-- =============================================================
-- D. RFM 用户分层 —— 找出高价值用户与流失预警
-- R=最近一次交易间隔天, F=交易次数, M=贡献手续费; NTILE 各分 5 档
-- =============================================================
WITH rfm AS (
    SELECT user_id,
           DATEDIFF('2026-07-01', MAX(DATE(ts))) AS recency,
           COUNT(*)                              AS frequency,
           SUM(fee)                              AS monetary
    FROM fact_trade
    GROUP BY user_id
),
scored AS (
    SELECT user_id, recency, frequency, monetary,
           NTILE(5) OVER (ORDER BY recency DESC)  AS r_score,  -- 越近分越高
           NTILE(5) OVER (ORDER BY frequency)     AS f_score,
           NTILE(5) OVER (ORDER BY monetary)      AS m_score
    FROM rfm
)
SELECT *,
       CASE
         WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN '核心鲸鱼'
         WHEN r_score >= 4 AND f_score <= 2                  THEN '新客/潜力'
         WHEN r_score <= 2 AND m_score >= 4                  THEN '高价值流失预警'
         WHEN r_score <= 2                                   THEN '一般流失'
         ELSE '普通活跃'
       END AS segment
FROM scored
ORDER BY monetary DESC;

-- D2. 各分层人数与手续费贡献占比(给运营看的汇总)
WITH rfm AS (
    SELECT user_id, DATEDIFF('2026-07-01', MAX(DATE(ts))) AS recency,
           COUNT(*) AS frequency, SUM(fee) AS monetary
    FROM fact_trade GROUP BY user_id
),
scored AS (
    SELECT user_id, monetary,
           NTILE(5) OVER (ORDER BY recency DESC) AS r,
           NTILE(5) OVER (ORDER BY frequency)    AS f,
           NTILE(5) OVER (ORDER BY monetary)     AS m
    FROM rfm
),
seg AS (
    SELECT CASE
             WHEN r >= 4 AND f >= 4 AND m >= 4 THEN '核心鲸鱼'
             WHEN r >= 4 AND f <= 2            THEN '新客/潜力'
             WHEN r <= 2 AND m >= 4            THEN '高价值流失预警'
             WHEN r <= 2                       THEN '一般流失'
             ELSE '普通活跃' END AS segment, monetary
    FROM scored
)
SELECT segment,
       COUNT(*)                                        AS users,
       ROUND(SUM(monetary), 2)                         AS fee_contrib,
       ROUND(100 * SUM(monetary) / SUM(SUM(monetary)) OVER (), 1) AS fee_pct
FROM seg
GROUP BY segment
ORDER BY fee_contrib DESC;

-- =============================================================
-- E. 营收拆解 —— 手续费收入靠哪些币种 / VIP 等级支撑
-- =============================================================

-- E1. 按币种(交易对基础币)
SELECT a.symbol, a.category,
       COUNT(*)                AS trades,
       ROUND(SUM(t.amount), 2) AS gmv,
       ROUND(SUM(t.fee), 2)    AS fee,
       ROUND(100 * SUM(t.fee) / SUM(SUM(t.fee)) OVER (), 1) AS fee_pct
FROM fact_trade t
JOIN dim_asset a ON a.asset_id = t.base_asset_id
GROUP BY a.symbol, a.category
ORDER BY fee DESC;

-- E2. 按 VIP 等级(高 VIP 费率低但可能量大 —— 看净贡献)
SELECT u.vip_level,
       COUNT(DISTINCT u.user_id) AS users,
       COUNT(t.trade_id)         AS trades,
       ROUND(SUM(t.amount), 2)   AS gmv,
       ROUND(SUM(t.fee), 2)      AS fee,
       ROUND(AVG(t.fee), 4)      AS avg_fee_per_trade
FROM dim_user u
LEFT JOIN fact_trade t ON t.user_id = u.user_id
GROUP BY u.vip_level
ORDER BY u.vip_level;

-- =============================================================
-- F. 渠道 ROI —— 哪个注册渠道来的用户最能贡献手续费
-- 业务解读: 指导市场预算往高产出渠道倾斜。
-- =============================================================
SELECT u.reg_channel,
       COUNT(DISTINCT u.user_id)                                     AS users,
       COUNT(DISTINCT CASE WHEN t.trade_id IS NOT NULL THEN u.user_id END) AS traders,
       ROUND(100 * COUNT(DISTINCT CASE WHEN t.trade_id IS NOT NULL THEN u.user_id END)
             / COUNT(DISTINCT u.user_id), 1)                         AS conv_rate,
       ROUND(COALESCE(SUM(t.fee), 0), 2)                             AS fee,
       ROUND(COALESCE(SUM(t.fee), 0) / COUNT(DISTINCT u.user_id), 2) AS fee_per_user
FROM dim_user u
LEFT JOIN fact_trade t ON t.user_id = u.user_id
GROUP BY u.reg_channel
ORDER BY fee_per_user DESC;

-- =============================================================
-- G. 挂单成交率 —— 产品体验/流动性指标
-- =============================================================
SELECT status,
       COUNT(*)                                              AS cnt,
       ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)      AS pct
FROM fact_order
GROUP BY status
ORDER BY cnt DESC;

-- =============================================================
-- H. 异常账户线索 —— 为 P5 风控/建模埋点(单用户成交额远超同层均值)
-- =============================================================
WITH per_user AS (
    SELECT user_id, SUM(amount) AS gmv, COUNT(*) AS trades
    FROM fact_trade GROUP BY user_id
),
stat AS (
    SELECT AVG(gmv) AS mu, STDDEV(gmv) AS sd FROM per_user
)
SELECT p.user_id, ROUND(p.gmv, 2) AS gmv, p.trades,
       ROUND((p.gmv - s.mu) / NULLIF(s.sd, 0), 2) AS z_score
FROM per_user p CROSS JOIN stat s
WHERE (p.gmv - s.mu) / NULLIF(s.sd, 0) > 3      -- 3 倍标准差以外
ORDER BY z_score DESC
LIMIT 50;

SELECT 'analysis queries done ✔' AS status;
