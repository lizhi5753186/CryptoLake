-- ADS 应用层: 每日营收大盘(直接喂给 BI 看板)
select
    trade_date,
    count(distinct user_id)  as dau,
    sum(trade_cnt)           as trades,
    round(sum(gmv), 2)       as gmv,
    round(sum(fee), 2)       as fee_revenue,
    round(sum(fee) / nullif(count(distinct user_id), 0), 4) as arpu_fee
from {{ ref('dws_user_daily') }}
group by trade_date
order by trade_date
