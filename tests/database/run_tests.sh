#!/bin/bash
# 数据库测试运行脚本

echo "=========================================="
echo "运行数据库测试"
echo "=========================================="

# 检查pytest是否安装
if ! python -m pytest --version > /dev/null 2>&1; then
    echo "错误: pytest未安装，请先安装: pip install pytest"
    exit 1
fi

# 运行所有数据库测试
echo ""
echo "运行所有数据库测试..."
python -m pytest tests/database/ -v --tb=short

echo ""
echo "=========================================="
echo "测试完成"
echo "=========================================="

