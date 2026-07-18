# 00 · 本地 MySQL 搭建(macOS)

> 目标:装好 MySQL 8.0+,能用命令行连上,建好 cryptolake 库。
> 为什么要 8.0+:项目大量用到**窗口函数**和 **CTE(WITH)**,5.7 不支持。

## 方式 A:Homebrew(推荐,最快)

```bash
# 1. 安装
brew install mysql

# 2. 启动(开机自启)
brew services start mysql

# 3. 初始化安全设置(设 root 密码,一路 y)
mysql_secure_installation
#   本项目脚本默认 root 密码是 root,你可以设成别的,
#   但记得同步改各脚本顶部的 DB_URL / 密码。

# 4. 验证登录
mysql -u root -p
```

登录进去后确认版本 ≥ 8.0:

```sql
SELECT VERSION();      -- 期望 8.0.xx 或 8.4.xx
```

## 方式 B:官方 DMG 安装包

1. 打开 https://dev.mysql.com/downloads/mysql/ 下载 macOS DMG。
2. 双击安装,安装过程中会给一个 **临时 root 密码**,记下来。
3. 系统设置里能看到 MySQL 面板,点 Start 启动。
4. 把 `/usr/local/mysql/bin` 加到 PATH:
   ```bash
   echo 'export PATH="/usr/local/mysql/bin:$PATH"' >> ~/.zshrc
   source ~/.zshrc
   ```
5. 首次登录后改密码:
   ```sql
   ALTER USER 'root'@'localhost' IDENTIFIED BY 'root';
   ```

## 建库建表 + 造数(核心步骤)

```bash
cd /Users/tommy/CryptoLake

# 1. 建库 + 8 张表
mysql -u root -p < sql/01_schema.sql

# 2. 装 Python 依赖(见 docs/01)后造数
python datagen/generate_data.py            # 默认 5000 用户
#   想放大规模(练大数据用):
# python datagen/generate_data.py --users 30000

# 3. 跑分析 SQL 看结果(也可以在 DBeaver / Navicat 里逐段执行)
mysql -u root -p cryptolake < sql/02_analysis.sql
```

## 图形化客户端(强烈推荐,写 SQL 更爽)

- **DBeaver**(免费开源):`brew install --cask dbeaver-community`
- **Navicat**(收费,界面友好,国内公司常用)
- VS Code 插件:MySQL / SQLTools

连接参数:主机 `127.0.0.1`,端口 `3306`,用户 `root`,密码 `root`,数据库 `cryptolake`。

## 常见坑

| 现象 | 原因 / 解决 |
|---|---|
| `Access denied for user 'root'` | 密码不对;或跳过密码用 `sudo mysql` 进去重设 |
| pymysql 报 `cryptography is required` | `pip install cryptography` |
| `caching_sha2_password` 连不上 | `ALTER USER 'root'@'localhost' IDENTIFIED WITH caching_sha2_password BY 'root';` |
| 造数很慢 | 正常,10 万级几分钟;放大到百万级用 `LOAD DATA` 或分批 |
| 窗口函数报语法错 | 你的 MySQL 是 5.7,请升级到 8.0 |
