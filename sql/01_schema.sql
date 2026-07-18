-- =============================================================
-- CryptoLake · 币安式加密交易平台数据仓库
-- 01_schema.sql —— 建库 + 星型模型 8 张表
-- 引擎 MySQL 8.0+ (需要窗口函数 / CTE)
-- 用法: mysql -u root -p < 01_schema.sql
-- =============================================================

DROP DATABASE IF EXISTS cryptolake;
CREATE DATABASE cryptolake
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_0900_ai_ci;
USE cryptolake;

-- -------------------------------------------------------------
-- 维度表 DIMENSIONS
-- -------------------------------------------------------------

-- 用户维度
CREATE TABLE dim_user (
    user_id      INT           NOT NULL PRIMARY KEY,
    reg_time     DATETIME      NOT NULL COMMENT '注册时间',
    country      VARCHAR(4)    NOT NULL COMMENT 'ISO 国家码',
    kyc_level    TINYINT       NOT NULL DEFAULT 0 COMMENT '实名等级 0未认证 1初级 2高级',
    reg_channel  VARCHAR(20)   NOT NULL COMMENT '注册渠道 organic/referral/ads_google/ads_twitter/kol',
    referrer_id  INT           NULL     COMMENT '邀请人 user_id, NULL 表示非邀请注册',
    vip_level    TINYINT       NOT NULL DEFAULT 0 COMMENT 'VIP 等级 0-5, 越高手续费越低',
    KEY idx_reg_time (reg_time),
    KEY idx_channel  (reg_channel),
    KEY idx_country  (country)
) COMMENT='用户维度表';

-- 资产(币种)维度
CREATE TABLE dim_asset (
    asset_id    INT          NOT NULL PRIMARY KEY,
    symbol      VARCHAR(16)  NOT NULL COMMENT '币种代码 BTC/ETH/...',
    asset_name  VARCHAR(32)  NOT NULL,
    category    VARCHAR(16)  NOT NULL COMMENT 'major主流 / altcoin山寨 / stablecoin稳定币',
    UNIQUE KEY uk_symbol (symbol)
) COMMENT='资产维度表';

-- 日期维度(做时间分析必备)
CREATE TABLE dim_date (
    date_id     DATE     NOT NULL PRIMARY KEY,
    year        SMALLINT NOT NULL,
    month       TINYINT  NOT NULL,
    day         TINYINT  NOT NULL,
    week        TINYINT  NOT NULL COMMENT 'ISO 周数',
    quarter     TINYINT  NOT NULL,
    is_weekend  TINYINT  NOT NULL COMMENT '1=周末'
) COMMENT='日期维度表';

-- -------------------------------------------------------------
-- 事实表 FACTS
-- -------------------------------------------------------------

-- 成交明细(平台收入之源: fee 字段)
CREATE TABLE fact_trade (
    trade_id      BIGINT        NOT NULL PRIMARY KEY,
    user_id       INT           NOT NULL,
    base_asset_id INT           NOT NULL COMMENT '交易对基础币, 计价币统一 USDT',
    symbol        VARCHAR(20)   NOT NULL COMMENT '交易对 如 BTC/USDT',
    side          ENUM('BUY','SELL') NOT NULL,
    price         DECIMAL(20,8) NOT NULL COMMENT '成交价(USDT)',
    qty           DECIMAL(24,8) NOT NULL COMMENT '成交数量(基础币)',
    amount        DECIMAL(24,8) NOT NULL COMMENT '成交额 price*qty (USDT)',
    fee           DECIMAL(20,8) NOT NULL COMMENT '手续费 (USDT)',
    ts            DATETIME      NOT NULL COMMENT '成交时间',
    KEY idx_user (user_id),
    KEY idx_ts   (ts),
    KEY idx_asset(base_asset_id),
    KEY idx_user_ts (user_id, ts)
) COMMENT='成交事实表';

-- 挂单(含撤单/未成交, 用于挂单成交率)
CREATE TABLE fact_order (
    order_id      BIGINT        NOT NULL PRIMARY KEY,
    user_id       INT           NOT NULL,
    base_asset_id INT           NOT NULL,
    side          ENUM('BUY','SELL') NOT NULL,
    price         DECIMAL(20,8) NOT NULL,
    qty           DECIMAL(24,8) NOT NULL,
    status        ENUM('FILLED','PARTIAL','CANCELED','OPEN') NOT NULL,
    create_ts     DATETIME      NOT NULL,
    update_ts     DATETIME      NOT NULL,
    KEY idx_user (user_id),
    KEY idx_status (status),
    KEY idx_create_ts (create_ts)
) COMMENT='挂单事实表';

-- 充值 / 提现
CREATE TABLE fact_deposit_withdraw (
    id         BIGINT        NOT NULL PRIMARY KEY,
    user_id    INT           NOT NULL,
    direction  ENUM('DEPOSIT','WITHDRAW') NOT NULL,
    asset_id   INT           NOT NULL,
    amount_usd DECIMAL(24,8) NOT NULL COMMENT '折算 USDT 金额',
    ts         DATETIME      NOT NULL,
    KEY idx_user (user_id),
    KEY idx_ts   (ts),
    KEY idx_dir  (direction)
) COMMENT='充提事实表';

-- 登录 / 活跃日志
CREATE TABLE fact_login (
    id        BIGINT      NOT NULL PRIMARY KEY,
    user_id   INT         NOT NULL,
    login_ts  DATETIME    NOT NULL,
    device    VARCHAR(10) NOT NULL COMMENT 'web/ios/android',
    KEY idx_user (user_id),
    KEY idx_ts   (login_ts)
) COMMENT='登录事实表';

-- 行情 K 线(日线 OHLCV)
CREATE TABLE fact_kline (
    id         BIGINT        NOT NULL PRIMARY KEY,
    asset_id   INT           NOT NULL,
    kline_date DATE          NOT NULL,
    open       DECIMAL(20,8) NOT NULL,
    high       DECIMAL(20,8) NOT NULL,
    low        DECIMAL(20,8) NOT NULL,
    close      DECIMAL(20,8) NOT NULL,
    volume     DECIMAL(24,8) NOT NULL,
    UNIQUE KEY uk_asset_date (asset_id, kline_date),
    KEY idx_date (kline_date)
) COMMENT='日K线行情事实表';

SELECT 'schema created ✔' AS status;
