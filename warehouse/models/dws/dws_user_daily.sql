-- DWS 轻度汇总层: 用户 × 日 粒度的交易汇总(下游多个报表复用)
select
    user_id,
    trade_date,
    count(*)                             as trade_cnt,
    sum(amount)                          as gmv,
    sum(fee)                             as fee,
    sum(case when side='BUY'  then amount else 0 end) as buy_amount,
    sum(case when side='SELL' then amount else 0 end) as sell_amount,
    count(distinct base_asset_id)        as asset_variety
from {{ ref('dwd_trade_detail') }}
group by user_id, trade_date
