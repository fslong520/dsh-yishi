#!/bin/bash
# 忆时记忆系统 TEST.sh — 验证引擎就绪，可在 kylinbot 中使用
set -e

echo "=== 忆时记忆系统 自检 ==="

# 1. 检查 memory_core.py
CORE=~/.local/share/忆时/scripts/memory_core.py
if [ -f "$CORE" ]; then
    echo "✓ memory_core.py 存在"
else
    echo "✗ memory_core.py 缺失 — 请安装 dsh-yishi 引擎: npm i -g @fslong/dsh-yishi"
    exit 1
fi

# 2. 检查数据目录
DATA=~/.local/share/忆时/data
if [ -d "$DATA" ]; then
    echo "✓ 数据目录 $DATA 存在"
else
    echo "✗ 数据目录不存在 — 请先运行 python3 $CORE import 初始化"
    exit 1
fi

# 3. 检查 python3 解释器
if command -v python3 &>/dev/null; then
    echo "✓ python3 可用"
else
    echo "✗ python3 不可用"
    exit 1
fi

# 4. 运行 recall 测试（快速验证引擎可用）
export MEMO_DIR="$DATA"
if python3 "$CORE" recall "测试" --limit 1 &>/dev/null; then
    echo "✓ 忆时引擎 recall 正常"
else
    echo "✗ 忆时引擎 recall 异常 — 请检查 python3 依赖与 chromadb"
    exit 1
fi

echo "=== 自检通过。忆时技能可正常使用 ==="