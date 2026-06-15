#!/bin/bash
# 知虾竞品监控系统安装脚本

set -e

echo "=================================="
echo "知虾竞品监控系统安装脚本"
echo "=================================="

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 创建必要的目录
echo "创建目录结构..."
mkdir -p data/downloads
mkdir -p output/consolidated
mkdir -p logs

# 检查Python版本
echo "检查Python版本..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
REQUIRED_VERSION="3.8"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "错误: 需要Python 3.8或更高版本，当前版本: $PYTHON_VERSION"
    exit 1
fi

echo "Python版本检查通过: $PYTHON_VERSION"

# 安装Python依赖
echo "安装Python依赖..."
pip3 install -r requirements.txt --break-system-packages

# 安装Playwright浏览器
echo "安装Playwright Chromium浏览器..."
python3 -m playwright install chromium --with-deps

# 创建符号链接（可选）
echo ""
echo "安装完成!"
echo ""
echo "下一步操作:"
echo "1. 编辑 config/competitors.yaml 配置你的监控参数"
echo "2. 运行测试: python3 scripts/zhixia_monitor.py status"
echo "3. 运行采集: python3 scripts/zhixia_monitor.py collect"
echo ""
echo "详细使用说明请查看 SKILL.md"
