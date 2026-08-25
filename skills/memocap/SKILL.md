---
name: memocap
description: "忆时记忆系统 - 类人记忆检索/存储/遗忘/胶囊/可视化。让 AI 拥有会遗忘、会联想、会涌现、会封存的记忆。触发词：忆时、记忆、记住、回想、回忆、recall、remember、时间胶囊、记忆检索、可视化、记忆脑图、人物画像。"
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
metadata:
  slug: memocap
  version: "2.4.0"
  trigger: 忆时, 记忆检索, 时间胶囊, 记忆胶囊, 回想, 回忆, recall, remember, /忆时, 记住, 可视化, 记忆脑图, 人物画像
---

# Skill: 忆时记忆系统

## Keywords
忆时, 记忆, 记忆检索, 记忆存储, 时间胶囊, 遗忘曲线, 记忆涌现, 视觉化, 记忆能力

## Summary
忆时是类人记忆系统。核心命令经 `memory_core.py` CLI 走混合检索（BM25+向量 RRF）、去重合并、遗忘曲线、情绪锚定。数据与脚本共享于本机 `~/.local/share/yishi/`（全英文目录，跨平台统一），多工具双栖共用。

## 前置（启始三检，每会话必行）
缺一不可，验不过即报不绕：
1. `MEMO_DIR` 已设环境变量？——否则脚本路径错、数据错存。
2. 数据目录 `~/.local/share/yishi/data` 存在且可写？
3. Python 解释器可用？`memory_core.py` 能否运行？（Linux/macOS 用 `python3`，Windows 用 `python`；脚本不硬编码解释器）

**环境自愈**：脚本报错（缺依赖/未初始化/模型缺失）时先自修再问人——`python3 ~/.local/share/yishi/scripts/install.py`（Windows: `python %USERPROFILE%\.local\share\yishi\scripts\install.py`），幂等一键装依赖+初始化+下模型；`--check` 复查「✓ 环境齐备」方止。仍败才报用户，附报错原文。

## 路径与命令
```bash
LOCAL_BASE=~/.local/share/yishi
YISHI=$LOCAL_BASE/scripts/memory_core.py
MEMO_DIR=$LOCAL_BASE/data
# Windows：%USERPROFILE%\.local\share\yishi 替 ~/.local/share/yishi，python 替 python3
# store：内容为【位置参数放最后】（无 --content/--tags），关键字用 --keywords；title ≤10 字自动生成，可 --title 覆盖
python3 $YISHI store --type <decision|task|preference|emotion|context|time|skill> --keywords "k1,k2" --emotion <0-1> "[完整内容]"
# recall：检索/核实
python3 $YISHI recall "关键词" --limit 5
# 其余子命令：forget 删除 | stats 统计 | export 导出 | recover 恢复 | capsule 时间胶囊
# 可视化：python3 $LOCAL_BASE/scripts/viz/viz.py（全景）/ mindmap.py（网状记忆图谱，D3 力导向）
# 人物画像：python3 $LOCAL_BASE/scripts/viz/profile.py
```

## 三条红线（铁律）
1. **言必检**——每言先 recall 检索再作答，检而再检，换词查透。
2. **值必存**——有价值信息（决策/偏好/任务/情绪/时间/上下文）主动留存，存后立刻 recall 核实。
3. **存必告**——存则告"已录"（指明类型），不存亦告，不沉默。

## 存储质量
记忆内容**不可压缩**（对话输出可省字，存储须自足）。内容按【前因】【行为】【后果】三要素，答得出"为何"与"何如"、三月后重读自能理解方存。宁多三行因果，不省一字。

## 语言风格
默认简约直给，去填充词、客套、自夸、工具调用叙述。安全警告/不可逆操作/多步易歧义处自动恢复正常句式，明晰为要。

## 模块详情
细册在 `~/.local/share/yishi/docs/modules/`（13-retrieval-store.md 检索存储、12-viz-profile.md 可视化画像、11-quick-commands.md 快捷命令等）。渐进式披露——遇场景才读对应模块，勿一次全读。
