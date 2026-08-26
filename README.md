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

1. 同步 `docs/` + `scripts/` 至 `~/.local/share/yishi/`（全英文目录，跨平台统一，Windows 中文路径易乱码）
2. 经 `systemPrompt.section` 注入记忆系统指令
3. 经 `ctx.skills.registerProvider` 注册 `memocap` 技能
4. 环境保障：Python 依赖缺失 → 后台装依赖；bge 模型缺失 → 后台下载

## 安装

```bash
# npm 安装
dsh plugin --profile web add @fslong/dsh-yishi

# 重启 DSH 生效
```

### 本地开发

```bash
cd ~/Documents/dsh-yishi
pnpm i && pnpm build

# 装进 profile
cd ~/.dsh/profiles/web
pnpm add file:~/Documents/dsh-yishi
```

## 首次使用（环境自愈）

插件已自动后台装依赖、下模型；若 AI 报"环境用不起来"（缺依赖/未初始化/模型缺失），AI 会自行运行自愈脚本；亦可手动：

```bash
# 一键全流程（依赖 + 初始化 + 模型，幂等，可反复跑）
python3 ~/.local/share/yishi/scripts/install.py
# Windows PowerShell（python 替 python3）
python $env:USERPROFILE\.local\share\yishi\scripts\install.py
# Windows cmd.exe
python %USERPROFILE%\.local\share\yishi\scripts\install.py

# 只检查缺什么
python3 ~/.local/share/yishi/scripts/install.py --check
```

## 嵌入模型

插件依赖 **bge-base-zh-v1.5**（~400MB）。首次安装时自动后台下载，无需操作。

若 AI 回复仍为现代汉语/英语（未出现鲁迅式半文半白风格），说明模型未装成功，手动执行：

```bash
python3 ~/.local/share/yishi/scripts/models-install.py
# Windows PowerShell / cmd.exe（python 替 python3，$env:USERPROFILE 或 %USERPROFILE% 替 ~）
python $env:USERPROFILE\.local\share\yishi\scripts\models-install.py
```

## 环境变量

| 变量 | 默认 | 说明 |
|------|------|------|
| `YISHI_DATA_DIR` | `~/.local/share/yishi` | 忆时根目录（数据+模型+脚本） |
| `MEMO_DIR` | `<YISHI_DATA_DIR>/data` | 记忆数据目录（Chroma 库） |
| `DSH_YISHI_DISABLE` | 未设 | `1` 禁用插件 |

## 命令速查

```bash
PY=~/.local/share/yishi/scripts/memory_core.py
export MEMO_DIR=~/.local/share/yishi/data
# Windows：PowerShell 用 `$env:USERPROFILE` + 花括号 `${env:USERPROFILE}`，cmd 用 `%USERPROFILE%`；python 替 python3

python3 $PY recall "关键词" --limit 5
python3 $PY store --type decision --keywords "k" --emotion 0.5 "内容"
python3 ~/.local/share/yishi/scripts/viz/viz.py
```

## 许可

MIT
