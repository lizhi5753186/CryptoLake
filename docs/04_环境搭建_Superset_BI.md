# 04 · BI 看板搭建(P5 交付物)

> 目标:做一个"运营监控看板",让非技术的人也能看懂平台经营状况。
> 三选一即可,**按你偏好和求职地区挑一个练熟**就行,别都学。

---

## 选项 1:Apache Superset(免费开源,数据人常用)

用 Docker 起最省事:

```bash
# 需先装 Docker Desktop
git clone https://github.com/apache/superset.git
cd superset
docker compose -f docker-compose-image-tag.yml up -d
#   访问 http://localhost:8088  默认账号 admin / admin
```

连 MySQL 数据源(在 Settings → Database Connections):
```
mysql+pymysql://root:root@host.docker.internal:3306/cryptolake
```
> Docker 里连宿主机 MySQL 用 `host.docker.internal`,不是 127.0.0.1。

然后建图表:直接基于 `ads_revenue_daily`、`ads_user_rfm` 两张表拖拽出:
- 每日 GMV / 手续费收入 折线图
- RFM 分层人数 & 手续费贡献 饼图/条形图
- DAU 趋势
- 按币种手续费 Top 榜

把这些图拼成一个 Dashboard,截图/录屏进作品集。

---

## 选项 2:Tableau Public(免费,界面最友好,外企/国际岗认可度高)

1. 下载 Tableau Public(免费版):https://public.tableau.com/
2. 免费版不能直连 MySQL,但可以:
   - 用 `analysis/analysis.py` 或一段 SQL 把结果导出成 CSV;
   - 或装 Tableau Desktop 试用版直连 MySQL。
3. 拖拽做图,发布到 Tableau Public 得到一个**公开链接**——
   直接贴进简历,面试官点开就能看,非常加分。

---

## 选项 3:FineBI / 帆软(国内公司,尤其传统/金融行业高频)

- 官网下个人免费版:https://www.finebi.com/
- 连 MySQL 数据源 → 基于 ads 表做仪表板。
- 国内不少 JD 直接写"熟悉帆软",练一下有针对性。

---

## 看板要放哪些指标(想清楚再动手)

一个好的运营看板 = **北极星指标 + 分解指标 + 健康度指标**:

| 区块 | 指标 |
|---|---|
| 北极星 | 手续费总收入 / GMV |
| 增长 | 新增用户、DAU/MAU、各渠道转化率 |
| 留存 | 7 日 / 30 日留存曲线 |
| 价值 | RFM 分层分布、核心鲸鱼贡献占比 |
| 风险 | 异常账户数、挂单撤单率 |

> 面试问"你这个看板给谁看、帮他做什么决策",能答清楚比图做得花哨重要得多。
