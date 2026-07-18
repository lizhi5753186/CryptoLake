#!/usr/bin/env bash
# =============================================================
# CryptoLake · GitHub 一键初始化脚本
# 作用: git init -> 首次提交 -> (可选)在 GitHub 建仓并推送
# 用法:
#   bash scripts/init_github.sh                  # 只本地初始化 + 首次提交
#   bash scripts/init_github.sh cryptolake       # 顺便在 GitHub 建同名仓库并推送
#   bash scripts/init_github.sh cryptolake public # 建成公开仓库(默认 private)
# 前置: 想推 GitHub 需先装并登录 gh:  brew install gh && gh auth login
# =============================================================
set -e
cd "$(dirname "$0")/.."          # 切到项目根目录
REPO_NAME="${1:-}"
VISIBILITY="${2:-private}"        # private / public

echo "▶ 项目目录: $(pwd)"

# 1. 初始化(若还不是 git 仓库)
if [ ! -d .git ]; then
  git init -b main
  echo "  git 仓库已初始化 (分支 main)"
else
  echo "  已是 git 仓库,跳过 init"
fi

# 2. 首次提交
git add .
if git diff --cached --quiet; then
  echo "  没有待提交的改动"
else
  git commit -m "init: CryptoLake 加密交易平台数据分析项目

- MySQL 星型模型 8 表 + Python 造数(真实分布)
- SQL 业务分析(漏斗/留存/RFM/营收/渠道/风控)
- Python 分析 + A/B 测试 + Jupyter 报告
- dbt 分层数仓 + Spark + Airflow + 流失预测模型
- 18 个月路线图(roadmap.html) + 简历模板(resume.html)

Co-Authored-By: Claude <noreply@anthropic.com>"
  echo "  首次提交完成 ✔"
fi

# 3. (可选)在 GitHub 建仓并推送
if [ -n "$REPO_NAME" ]; then
  if ! command -v gh >/dev/null 2>&1; then
    echo "  ⚠️ 未安装 gh CLI,跳过建仓。手动做法:"
    echo "     在 GitHub 网页建空仓库后执行:"
    echo "     git remote add origin git@github.com:<你的用户名>/$REPO_NAME.git"
    echo "     git push -u origin main"
    exit 0
  fi
  if ! gh auth status >/dev/null 2>&1; then
    echo "  ⚠️ gh 未登录,请先运行:  gh auth login"
    exit 1
  fi
  echo "▶ 在 GitHub 创建 $VISIBILITY 仓库 $REPO_NAME 并推送..."
  gh repo create "$REPO_NAME" --"$VISIBILITY" --source=. --remote=origin --push
  echo "  完成 ✔  打开看看:  gh repo view --web"
fi

echo "✅ 全部完成"
