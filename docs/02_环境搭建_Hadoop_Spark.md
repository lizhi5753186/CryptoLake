# 02 · Hadoop / Spark 搭建(macOS 单机)

> 目标:理解大数据栈,能用 Spark SQL 跑分析。
> **心态**:数据分析师**不需要**运维 Hadoop 集群,面试也很少考安装细节。
> 你要会的是 **Spark SQL / Hive SQL 的写法** 和 **"为什么要用它"**(数据量大到
> 单机 MySQL 扛不住时,分布式计算横向扩展)。所以本篇给两条路,**优先走路 A**。

---

## 路 A(推荐):只装 Spark,跳过 Hadoop

单机学 Spark SQL 完全不需要 Hadoop / HDFS,直接读 MySQL 或本地 Parquet 即可。

```bash
# 1. 装 Java(Spark 依赖 JDK 11 或 17)
brew install openjdk@17
echo 'export JAVA_HOME=$(/usr/libexec/java_home -v 17)' >> ~/.zshrc
source ~/.zshrc
java -version

# 2. 装 Spark(含 pyspark)
pip install pyspark==3.5.3      # 已在 requirements 里

# 3. 下载 MySQL JDBC 驱动(让 Spark 能连 MySQL)
#    https://dev.mysql.com/downloads/connector/j/  选 Platform Independent
#    解压得到 mysql-connector-j-8.x.x.jar,记住路径

# 4. 跑 Spark 分析
spark-submit --jars /你的路径/mysql-connector-j-8.4.0.jar spark/spark_analysis.py
```

验证 Spark 能起来:

```bash
pyspark        # 进入交互式 shell,能看到 SparkSession 就 OK,exit() 退出
```

---

## 路 B(进阶,想完整体验):装 Hadoop + Hive

只在你想在简历写"搭过 Hadoop/Hive 环境"时做。

```bash
# 1. Hadoop
brew install hadoop
#    配置在 /opt/homebrew/opt/hadoop/libexec/etc/hadoop/ 下:
#    core-site.xml   -> fs.defaultFS = hdfs://localhost:9000
#    hdfs-site.xml   -> dfs.replication = 1(单机)
#    配 SSH 免密: ssh-keygen 然后 ssh-copy-id localhost

# 2. 格式化并启动
hdfs namenode -format
start-dfs.sh              # 访问 http://localhost:9870 看 HDFS
start-yarn.sh             # 访问 http://localhost:8088 看 YARN

# 3. Hive
brew install hive
schematool -dbType derby -initSchema
hive                     # 进入 Hive CLI 写 HQL
```

> Hive SQL 语法和本项目的 MySQL 分析 SQL 高度相似(窗口函数、CTE 都支持),
> 你可以把 `sql/02_analysis.sql` 的查询几乎原样搬到 Hive 里跑。

---

## 数仓分层怎么落到 Spark/Hive

项目已在 `warehouse/`(dbt)里定义了 ODS→DWD→DWS→ADS 分层。
概念迁移到大数据栈:

| 层 | 含义 | 在本项目 |
|---|---|---|
| ODS | 贴源,原始数据 | `ods_trade`(fact_trade 映射) |
| DWD | 明细清洗 + 维度退化 | `dwd_trade_detail` |
| DWS | 轻度汇总(用户×日) | `dws_user_daily` |
| ADS | 应用/报表层 | `ads_revenue_daily` / `ads_user_rfm` |

面试能把这张表讲清楚 + 说明"为什么要分层(解耦、复用、可维护)",就到位了。

## 常见坑

| 现象 | 解决 |
|---|---|
| `JAVA_HOME is not set` | 按上面配 JAVA_HOME,注意 Spark 3.5 用 JDK 11/17,别用 21 |
| Spark 连 MySQL `No suitable driver` | `--jars` 没带对 jar,或路径错 |
| Hadoop 启动 `Permission denied (publickey)` | SSH 免密没配好,`ssh localhost` 先能通 |
| 端口冲突 | 9000/9870/8088 被占,改配置或杀进程 |
