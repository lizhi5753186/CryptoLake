-- ODS 贴源层: 原样映射 fact_trade, 仅做字段规范, 不做业务加工
select
    trade_id,
    user_id,
    base_asset_id,
    symbol,
    side,
    price,
    qty,
    amount,
    fee,
    ts
from cryptolake.fact_trade
