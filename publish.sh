#!/bin/bash
# ============================================================
# GitHub Publish Script — AI Learning Assistant v1.0.0
# ============================================================
# 使用方法：
#   1. 将此脚本放置到项目根目录
#   2. 修改 YOUR_GITHUB_USERNAME 为你的 GitHub 用户名
#   3. 执行: chmod +x publish.sh && ./publish.sh
# ============================================================

YOUR_USERNAME="YOUR_GITHUB_USERNAME"
REPO_NAME="ai-learning-assistant"

echo "========================================"
echo "  1. 创建 GitHub 仓库"
echo "========================================"

gh repo create $REPO_NAME \
  --public \
  --description "Multi-agent AI learning assistant powered by FastAPI, LangGraph and RAG" \
  --source . \
  --remote origin \
  --push

echo ""
echo "========================================"
echo "  2. 推送代码"
echo "========================================"

git branch -M main
git remote add origin https://github.com/$YOUR_USERNAME/$REPO_NAME.git
git push -u origin main

echo ""
echo "========================================"
echo "  3. 创建 v1.0.0 Release"
echo "========================================"

gh release create v1.0.0 \
  --title "AI Learning Assistant v1.0.0" \
  --notes-file RELEASE_NOTES_v1.0.0.md

echo ""
echo "========================================"
echo "  ✅ Release Complete"
echo "========================================"
echo "  URL: https://github.com/$YOUR_USERNAME/$REPO_NAME"
echo "  Release: https://github.com/$YOUR_USERNAME/$REPO_NAME/releases/tag/v1.0.0"
