# @fslong/dsh-yishi

DSH 插件——为 AI Agent 提供类人记忆系统。

## 功能

- **混合检索**：BM25 关键词 + 向量语义双路 RRF 融合
- **遗忘曲线**：记忆随时间自然衰减
- **情绪锚定**：高情绪记忆权重更高，不易遗忘
- **记忆涌现**：话题转换时发现隐藏关联，主动联想
- **时间胶囊**：封存记忆，设定解锁日期
- **去重合并**：相似度 >90% 自动合并
- **可视化全景**：一键生成记忆全景 HTML
- **人物画像**：基于记忆数据生成分析报告

## 工作原理

插件 `apply` 时：

1. 同步 `docs/` + `scripts/` 至 `~/.local/share/忆时/`
2. 经 `systemPrompt.section` 注入记忆系统指令
3. 经 `ctx.skills.registerProvider` 注册 `memocap` 技能

## 安装

```bash
# npm 安装
dsh plugin --profile web add @fslong/dsh-yishi

# 重启 DSH 生效
```

### 本地开发

```bash
cd ~/Documents/yishi
pnpm i && pnpm build

# 装进 profile
cd ~/.dsh/profiles/web
pnpm add file:~/Documents/yishi
```

## 模型安装（必做）

插件依赖 **bge-base-zh-v1.5**（~400MB），需手动安装：

```bash
python3 ~/.local/share/忆时/scripts/models-install.py
```

## 环境变量

| 变量 | 默认 | 说明 |
|------|------|------|
| `YISHI_DATA_DIR` | `~/.local/share/忆时` | 数据目录 |
| `DSH_YISHI_DISABLE` | 未设 | `1` 禁用插件 |

## 命令速查

```bash
PY=~/.local/share/忆时/scripts/memory_core.py
export MEMO_DIR=~/.local/share/忆时/data

python3 $PY recall "关键词" --limit 5
python3 $PY store --type decision --keywords "k" --emotion 0.5 "内容"
python3 ~/.local/share/忆时/scripts/viz/viz.py
```

## 许可

MIT
