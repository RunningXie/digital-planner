#!/bin/bash
# Digital Planner - GitHub 推送脚本
# 使用方法: bash push_to_github.sh

echo "🚀 开始推送 Digital Planner 到 GitHub..."

cd "$(dirname "$0")"

# 1. 初始化 Git 仓库
if [ ! -d ".git" ]; then
    echo "📦 初始化 Git 仓库..."
    git init
fi

# 2. 添加所有文件
echo "📝 添加文件到 Git..."
git add .

# 3. 提交
echo "💾 提交代码..."
git commit -m "feat: initial commit - Digital Planner for English writing practice with AI corrections

Features:
- User authentication system with JWT
- Diary writing with AI-powered sentence-by-sentence corrections
- Phrase search with streaming AI responses and caching
- English learning assistant for writing practice

Tech Stack:
- FastAPI + SQLAlchemy
- SQLite/PostgreSQL
-智谱GLM-4.5-Air AI
- Docker support"

# 4. 创建 GitHub 仓库并推送
echo "🌐 创建 GitHub 仓库..."
gh repo create digital-planner --public --description "A warm digital planner for English writing practice with AI corrections" --source=. --remote=origin --push

echo ""
echo "✅ 完成！访问 https://github.com/$(gh api user --jq .login)/digital-planner"
