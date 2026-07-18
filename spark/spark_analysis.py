#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CryptoLake · P4 Spark SQL 版本
============================
把 MySQL 里的分析用 Spark 跑一遍 —— 数据量放大后单机 MySQL 吃力,
Spark 能水平扩展。这里演示 Spark 通过 JDBC 读 MySQL, 用 Spark SQL 做同样的
留存 / RFM / 营收分析, 结果可写回 MySQL 的 ADS 层或存成 Parquet。

前置: 安装 pyspark, 下载 mysql-connector-j jar(见 docs/02)。
用法:
  spark-submit --jars /path/mysql-connector-j-8.x.jar spark/spark_analysis.py
或本地:
  python spark/spark_analysis.py   (需 SPARK 环境)
"""
from pyspark.sql import SparkSession

JDBC = "jdbc:mysql://127.0.0.1:3306/cryptolake?useSSL=false&serverTimezone=UTC"
PROPS = {"user": "root", "password": "root", "driver": "com.mysql.cj.jdbc.Driver"}


def main():
    spark = (SparkSession.builder
             .appName("CryptoLake-SparkSQL")
             .config("spark.sql.shuffle.partitions", "8")
             .getOrCreate())
    spark.sparkContext.setLogLevel("WARN")

    def load(table):
        return spark.read.jdbc(JDBC, table, properties=PROPS)

    load("fact_trade").createOrReplaceTempView("fact_trade")
    load("dim_user").createOrReplaceTempView("dim_user")
    load("dim_asset").createOrReplaceTempView("dim_asset")

    print("===== 1) 手续费营收 Top 币种 =====")
    spark.sql("""
        SELECT a.symbol, COUNT(*) trades,
               ROUND(SUM(t.fee),2) fee
        FROM fact_trade t JOIN dim_asset a ON a.asset_id=t.base_asset_id
        GROUP BY a.symbol ORDER BY fee DESC
    """).show(truncate=False)

    print("===== 2) RFM 分层(Spark 窗口函数 NTILE) =====")
    rfm = spark.sql("""
        WITH rfm AS (
            SELECT user_id,
                   DATEDIFF(DATE '2026-07-01', MAX(TO_DATE(ts))) recency,
                   COUNT(*) frequency, SUM(fee) monetary
            FROM fact_trade GROUP BY user_id)
        SELECT user_id, recency, frequency, monetary,
               NTILE(5) OVER (ORDER BY recency DESC) r,
               NTILE(5) OVER (ORDER BY frequency)    f,
               NTILE(5) OVER (ORDER BY monetary)     m
        FROM rfm
    """)
    rfm.createOrReplaceTempView("rfm_scored")
    spark.sql("""
        SELECT CASE WHEN r>=4 AND f>=4 AND m>=4 THEN '核心鲸鱼'
                    WHEN r<=2 AND m>=4 THEN '高价值流失预警'
                    WHEN r<=2 THEN '一般流失' ELSE '普通活跃' END segment,
               COUNT(*) users, ROUND(SUM(monetary),2) fee
        FROM rfm_scored GROUP BY 1 ORDER BY fee DESC
    """).show(truncate=False)

    # 写回 ADS 层示例(取消注释即可):
    # rfm.write.mode("overwrite").jdbc(JDBC, "ads_user_rfm", properties=PROPS)
    # 或存 Parquet(数据湖):
    # rfm.write.mode("overwrite").parquet("/data/cryptolake/ads_user_rfm")

    print("✔ Spark 分析完成")
    spark.stop()


if __name__ == "__main__":
    main()
