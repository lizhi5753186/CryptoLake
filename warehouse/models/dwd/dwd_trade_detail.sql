-- DWD 明细层: 清洗 + 维度退化(把常用维度字段拼进明细, 减少下游 join)
-- 过滤脏数据(金额<=0), 打上日期/币种类别标签
with t as (
    select * from {{ ref('ods_trade') }}
)
select
    t.trade_id,
    t.user_id,
    t.base_asset_id,
    a.symbol            as asset_symbol,
    a.category          as asset_category,
    t.side,
    t.price,
    t.qty,
    t.amount,
    t.fee,
    t.ts,
    date(t.ts)          as trade_date,
    hour(t.ts)          as trade_hour,
    u.reg_channel,
    u.vip_level,
    u.country
from t
join cryptolake.dim_asset a on a.asset_id = t.base_asset_id
join cryptolake.dim_user  u on u.user_id  = t.user_id
where t.amount > 0
