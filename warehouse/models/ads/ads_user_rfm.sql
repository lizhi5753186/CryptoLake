-- ADS 应用层: 用户 RFM 分层结果表(供运营圈人 / 看板)
with rfm as (
    select
        user_id,
        datediff(date '2026-07-01', max(trade_date)) as recency,
        sum(trade_cnt)                               as frequency,
        sum(fee)                                     as monetary
    from {{ ref('dws_user_daily') }}
    group by user_id
),
scored as (
    select *,
        ntile(5) over (order by recency desc) as r_score,
        ntile(5) over (order by frequency)    as f_score,
        ntile(5) over (order by monetary)     as m_score
    from rfm
)
select *,
    case
        when r_score >= 4 and f_score >= 4 and m_score >= 4 then '核心鲸鱼'
        when r_score >= 4 and f_score <= 2                  then '新客/潜力'
        when r_score <= 2 and m_score >= 4                  then '高价值流失预警'
        when r_score <= 2                                   then '一般流失'
        else '普通活跃'
    end as segment
from scored
