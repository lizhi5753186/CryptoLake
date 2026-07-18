#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CryptoLake · P4 Airflow 调度 DAG
==============================
把整条链路编排成每日自动运行的管道:
    build_schema(仅首次) -> generate_data -> dbt_run -> dbt_test
    -> python_analysis -> churn_model

部署: 把本文件放到 $AIRFLOW_HOME/dags/ 下, 在 Airflow UI 里开启即可。
说明: 这里用 BashOperator 调用项目脚本; 生产环境更推荐用
      对应的 Operator(如 DbtRunOperator)。
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

PROJECT = "/Users/tommy/CryptoLake"     # 改成你的项目路径

default_args = {
    "owner": "cryptolake",
    "retries": 1,
    "retry_delay": timedelta(minutes=3),
}

with DAG(
    dag_id="cryptolake_pipeline",
    description="加密交易平台数据管道: 造数->dbt建模->分析->建模",
    default_args=default_args,
    start_date=datetime(2026, 1, 1),
    schedule="0 2 * * *",          # 每天凌晨 2 点
    catchup=False,
    tags=["cryptolake", "data-analyst"],
) as dag:

    generate_data = BashOperator(
        task_id="generate_data",
        bash_command=f"cd {PROJECT} && python datagen/generate_data.py --users 5000",
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"cd {PROJECT}/warehouse && dbt run",
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"cd {PROJECT}/warehouse && dbt test",
    )

    python_analysis = BashOperator(
        task_id="python_analysis",
        bash_command=f"cd {PROJECT} && python analysis/analysis.py",
    )

    churn_model = BashOperator(
        task_id="churn_model",
        bash_command=f"cd {PROJECT} && python ml/churn_model.py",
    )

    # 依赖关系
    generate_data >> dbt_run >> dbt_test >> python_analysis >> churn_model
