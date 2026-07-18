# 03 · dbt + Airflow 搭建

> 目标:用 dbt 把分层建模工程化,用 Airflow 把整条链路自动调度。
> 这两个是"数据工程化"的加分项,做出来简历上很亮眼。

---

## dbt(数据转换 / 分层建模)

```bash
# 1. 装(在项目虚拟环境里)
pip install dbt-core==1.8.7 dbt-mysql==1.8.0

# 2. 配连接:把示例 profile 拷到 ~/.dbt/
mkdir -p ~/.dbt
cp warehouse/profiles.example.yml ~/.dbt/profiles.yml
#    按需改里面的密码

# 3. 进项目目录,测试连接
cd warehouse
dbt debug            # 全绿表示连上了

# 4. 跑模型(按 ODS->DWD->DWS->ADS 依赖自动排序执行)
dbt run
#    生成的表在数据库里:ods_trade / dwd_trade_detail /
#    dws_user_daily / ads_revenue_daily / ads_user_rfm

# 5. 跑数据质量测试(unique / not_null / 取值范围)
dbt test

# 6. 生成 + 浏览数据血缘文档(面试可展示!)
dbt docs generate
dbt docs serve       # 浏览器看 lineage 血缘图
```

> `dbt test` 全绿 + 一张血缘图,是"我做过数据质量保障"的最好证据。

### dbt-mysql 装不上怎么办

dbt-mysql 有时和新版本 dbt-core 不兼容。备选:
- 用 **dbt-duckdb**(把 CSV 导进 DuckDB,零配置,学分层概念足够);
- 或直接把 `warehouse/models/**.sql` 里的 `{{ ref(...) }}` 换成真实表名,
  当普通 SQL 在 MySQL 里按顺序跑 —— 分层思想不变。

---

## Airflow(任务调度)

```bash
# 1. 装(建议单独虚拟环境,Airflow 依赖较重)
pip install "apache-airflow==2.10.3"

# 2. 初始化
export AIRFLOW_HOME=~/airflow
airflow db migrate
airflow users create --username admin --password admin \
    --firstname a --lastname b --role Admin --email a@b.com

# 3. 把本项目 DAG 拷到 dags 目录
mkdir -p ~/airflow/dags
cp airflow/cryptolake_dag.py ~/airflow/dags/
#    ⚠️ 打开该文件把 PROJECT 路径改成 /Users/tommy/CryptoLake

# 4. 启动(两个终端 or 用 standalone)
airflow standalone        # 一条命令起全套,访问 http://localhost:8080

# 5. 在 UI 里找到 cryptolake_pipeline,打开开关,点 Trigger 手动跑一次
```

DAG 依赖链:`generate_data → dbt_run → dbt_test → python_analysis → churn_model`

## 常见坑

| 现象 | 解决 |
|---|---|
| `dbt debug` 连不上 | profiles.yml 密码/端口不对;dbt-mysql 需要本机 ODBC 驱动 |
| Airflow 装依赖冲突 | 用官方 constraints 文件:`pip install "apache-airflow==2.10.3" --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.10.3/constraints-3.12.txt"` |
| DAG 不显示 | 文件语法错;看 `airflow dags list-import-errors` |
| task 报路径找不到 | DAG 里的 PROJECT 变量没改对 |
