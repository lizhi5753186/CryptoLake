# 01 · Python 环境搭建

> 目标:用虚拟环境隔离依赖,装好 pandas / sklearn 等,能跑造数和分析脚本。

## 1. 装 Python(建议 3.11 或 3.12)

```bash
brew install python@3.12
python3 --version        # 确认 ≥ 3.11
```

## 2. 建虚拟环境(养成好习惯,别污染全局)

```bash
cd /Users/tommy/CryptoLake
python3 -m venv .venv
source .venv/bin/activate        # 每次开新终端都要先 activate
#   退出用: deactivate
```

激活后命令行前面会出现 `(.venv)`。

## 3. 装依赖

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> pyspark / dbt / airflow 在 requirements 里默认注释或独立,按需装。
> 只做 P1–P3 的话,不用装它们。

## 4. 跑通三个核心脚本

```bash
# 造数(先确保 MySQL 已建库,见 docs/00)
python datagen/generate_data.py

# Python 分析 + 出图 + A/B 测试
python analysis/analysis.py
#   图表输出在 analysis/output/*.png

# 流失预测模型
python ml/churn_model.py
```

## 5. 用 Jupyter 做交互式分析(强烈推荐,做作品集展示用)

```bash
jupyter lab
```

浏览器会打开,新建 Notebook,把 `analysis/analysis.py` 里的函数拆成一格一格跑,
边写边看图 —— 这就是数据分析师的日常工作方式,也是面试演示的最佳载体。

## 常见坑

| 现象 | 解决 |
|---|---|
| `command not found: python` | 用 `python3`;或 `alias python=python3` |
| pip 装 numpy/scipy 很慢 | 换清华源:`pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt` |
| matplotlib 中文乱码 | 图里已尽量用英文标题;需中文可设 `plt.rcParams['font.sans-serif']=['PingFang SC']` |
| `ModuleNotFoundError` | 确认已 `source .venv/bin/activate` 再 pip install |
