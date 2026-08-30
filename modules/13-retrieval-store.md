# 模块 13 - 记忆操作流程（检索与存储细则）

**何时读**：对话启始取项目名、用户每言必检（涌现检索/情绪锚定）、主动存储、检索结果不足需升级、做决策或提问之前。此乃每言必检之详细执行档，日常对话高频场景触发。

> ⚡ **解释器平台适配**：本模块命令示例皆 `python3`（Linux/macOS）。**Windows 用 `python` 替换 `python3`**（或 `py -3`）；路径 `~/.local/share/yishi` 换 `$env:USERPROFILE\.local\share\yishi`（PowerShell，接子路径用 `${env:USERPROFILE}\.local\...`）或 `%USERPROFILE%\.local\share\yishi`（cmd.exe）。凡报错先走「环境自愈」节（见 yishi-instructions.md）——`install.py` 一键装依赖/初始化/下模型，勿硬扛。

## 对话启始——项目记忆检索

取工作目录之末尾目录名（即项目名）：
```bash
MEMO_DIR=~/.local/share/yishi/data python3 ~/.local/share/yishi/scripts/memory_core.py recall "项目名" --limit 3 --expand
```
若项目无关，则取其父目录名再试。过去涉及该项目之决策、偏好、任务皆可浮现。

**同时检查记忆梳理状态**（见 modules/10-consolidation.md「记忆自动梳理」）。

## 用户发言后——强涌现检索（每言必检）

**每一条用户消息，不论内容，皆须触发涌现检索。** 此非可选，乃强制流程。

**第零轮（并行触发）：**
收到用户消息后，立即以 background 任务发起语义检索，与分析用户意图并行执行：
```bash
MEMO_DIR=~/.local/share/yishi/data python3 ~/.local/share/yishi/scripts/memory_core.py recall "用户发言核心关键词" --limit 3 --expand
```
检索结果须在本次回复结束前收集并体现。

**第一轮：语义检索**
```bash
MEMO_DIR=~/.local/share/yishi/data python3 ~/.local/share/yishi/scripts/memory_core.py recall "用户发言关键词" --limit 3 --expand
```

**第二轮：涌现判定（强制）**
观第一轮结果：
- 若有 `[关联]` 标记项 → 已现涌现，直接表达："说到此，忆起一事……"
- 若结果 ≥ 2 条 → 取 top-2 之关键字/内容，构建复合查询，做第二轮涌现检索：
  ```bash
  MEMO_DIR=~/.local/share/yishi/data python3 ~/.local/share/yishi/scripts/memory_core.py recall "原关键词 新关键词" --limit 3
  ```
- 若第二轮结果与第一轮不重叠 → 此乃涌现之记忆，主动提及
- **仅1条亦须审视**：哪怕是单条，若语义沾边，即应表达关联——降低涌现门槛

**第三轮：情绪锚定（强制）**
每轮都查情绪锚定，而非仅"情绪显著时"。以情绪倾向词 + 话题词检索：
```bash
MEMO_DIR=~/.local/share/yishi/data python3 ~/.local/share/yishi/scripts/memory_core.py recall "话题词 情绪倾向" --type-filter emotion --min-weight 0.5 --limit 3
```

**涌现表达原则：**
- 宁可多提，不可漏提。涌现之记忆即使不完全吻合，亦值得抛出供用户确认。
- 表达须简洁，三五句话内。例："说起X，忆及之前你提过Y……可有参考价值？"

## 检索升级（穷尽模式）

当涌现检索产出不足时，不可就此罢休，需逐级加码：

| 级数 | 触发条件 | 行动 |
|------|----------|------|
| L0 | 首次出现的话题 | 标准四轮检索，正常表达 |
| L1 | 同一话题重复出现（2次+） | `--limit 3` + 跨类型搜索，另取近义词再检索一轮 |
| L2 | 检索为空 | 换2-3组不同角度关键词，逐组重试 |
| L3 | 检索仅1条 | 以该条关键词做二次扩散检索 |
| L4 | 用户情绪强烈 | 情绪锚定权重提升至 `--min-weight 0.7`，重点搜emotion类型 |

**穷尽铁律：** 检索结果为空，不意味着无关联记忆。两轮搜索无果方可放行，不可一次空就跳过。

**命令示例（深度检索）：**
```bash
# L1 加深：跨类型搜索（默认3条最相关）
MEMO_DIR=~/.local/share/yishi/data python3 ~/.local/share/yishi/scripts/memory_core.py recall "用户话题关键词" --limit 3 --expand

# L2 换角度：近义词/同义表达
MEMO_DIR=~/.local/share/yishi/data python3 ~/.local/share/yishi/scripts/memory_core.py recall "近义词" --limit 3 --expand

# L3 扩散检索：以命中条的关键词延伸
MEMO_DIR=~/.local/share/yishi/data python3 ~/.local/share/yishi/scripts/memory_core.py recall "已有结果的关键词 新角度" --limit 3 --expand

# L4 情绪锚定强搜索
MEMO_DIR=~/.local/share/yishi/data python3 ~/.local/share/yishi/scripts/memory_core.py recall "话题词 情绪词" --type-filter emotion --min-weight 0.7 --limit 3
```

## 主动存储——激进策略

用户言"记住"、"记下来"、"保存"时必存；此外，凡值得将来回顾者，皆主动存储。

**触发场景扩展（不限于对话结束）：**
- 旧有触发：用户透露新偏好、做出关键决定、交付重要上下文、情绪显著波动
- **新增触发——每次完成任务后：**
  - 标记 todo 为 `completed` 之时
  - 收 delegation 结果并验证通过之时
  - 完成一轮修改变更之后
  - 给用户输出实质结果（代码/文档/分析）之后
- **新增触发——定期自动提取**：对话每满 5 轮自动提取一次（见 modules/09-archiving.md「定期自动提取」），提取须过质量门过滤无用信息
- **凡以上任一场景，皆停顿自问：** "此次产出/发现/决策中，有无值得将来回顾者？"

**判定原则：**
- 有 → 提取 2-3 关键词，检索旧忆后再决定新增还是更新
- 无 → 静默跳过，无需告知
- 宁多勿少：反正本地存储，激进胜过保守
- **存时决策（2026-08-22 定稿）**：store 默认检索语义相似≥70% 候选簇并**完整打印候选原文**，AI 读取后决策：能综合合并→`--merge-ids` 删旧存新（综合版）；不能→机械存储兜底（`--force` 静默）。**决策权在 AI**，脚本不自动拼不自动删。

**存储质量门（存储前必过三问）：**
```
① 此记忆被 recall 时，能否助我直接行动或讨论？若需原对话上下文才懂→不合格
② 内容是否覆盖"重点+做法+上下文"三维？至少两维→合格，仅一维→补之
③ 是否有具体信息而非空泛标签？如"用户偏好AI内容"→空洞，"用户关注Naval Podcast五项AI框架"→合格
```
凡不过三问者，扩充后再存。

**前因后果铁律（用户 2026-08-09 明确要求）：** 存时必记因果链，不得只记"果"漏"因"。内容按【前因】→【行为】→【后果】三要素审视：
- **前因**：为什么发生？背景、触发条件、决策理由
- **行为**：发生了什么？做了什么、怎么做的
- **后果**：影响如何？修了什么、产出什么、后续待决什么

**自查**：若 content 只答"做了什么"而答不出"为何做"与"做完何如"，判不合格，补之再存。宁多三行因果，不省一字。

**存储命令：**（内容为位置参数放最后，勿用 `--content`/`--tags`；关键字用 `--keywords`）
```bash
# 默认：存前检索相似≥70%候选，完整打印候选原文供 AI 读取判断；机械存储兜底
MEMO_DIR=~/.local/share/yishi/data python3 ~/.local/share/yishi/scripts/memory_core.py store "内容" --type 类型 --emotion 情绪 --keywords "关键字"
# AI 判不能合并：静默强制新增
MEMO_DIR=~/.local/share/yishi/data python3 ~/.local/share/yishi/scripts/memory_core.py store "内容" --type 类型 --force
# AI 判能合并：删指定旧记忆(逗号分隔)，本内容(综合合并版)存为新条目
MEMO_DIR=~/.local/share/yishi/data python3 ~/.local/share/yishi/scripts/memory_core.py store "综合合并版" --type 类型 --merge-ids "旧ID1,旧ID2"
```
**存时决策流程（AI 主导）**：
1. store 打印相似≥70% 候选的**完整原文**（非片段）——AI 必须读到全文才能判断。
2. **能综合合并**（同主题碎片/矛盾可消）→ 写综合合并版（前因/行为/后果、矛盾以后来者为准），`--merge-ids` 删旧存新。
3. **不能合并**（仅字面相似、实不同主题）→ 机械存储已兜底，或 `--force` 静默。
4. 三条红线照常：存必核（读回确认）、存必告（告知机械存储 or 有机合并）。
**title 字段**：store 自动生成（`make_title` 取内容首段，≤10 字）供图谱节点标签。可不传，自动即够；特殊情形可 `--title` 覆盖。

**语义合并命令（merge，2026-08-22 立）：** 梳理时高相关记忆**靠语义检索合并，非字符串**。autostore 去重仅在相似≥90% 机械拼接内容（`旧。新`），措辞稍异即分家致同主题多条矛盾——故梳理须用 `merge` 语义识簇、AI 手写权威版、删旧。
```bash
# ① 预览：以某条记忆为锚，向量语义找出相似≥阈值的簇（dry-run，不删）
MEMO_DIR=~/.local/share/yishi/data python3 ~/.local/share/yishi/scripts/memory_core.py \
  merge --id <锚ID> --threshold 0.68 [--keyword "过滤词"]   # keyword 按候选 keywords 字段收窄

# ② AI 逐条读簇内原文，写权威合并版（前因/行为/后果）
# ③ 真正合并删旧：--content 必须为 AI 手写权威版
MEMO_DIR=~/.local/share/yishi/data python3 ~/.local/share/yishi/scripts/memory_core.py \
  merge --id <锚ID> --content "权威合并版全文" --keywords "新关键字" --emotion 0.6 --apply
```
- 锚 ID 保留，权威版写入该 ID 加 `consolidated` 标签；簇内其余逐条 delete。
- **迭代收敛**：同一主题多锚各跑一次、逐步降阈值/换关键词语，直到不再出现高相关簇为止（相似度 <0.70 的同主题会漏，须多次 merge）。
- 违背**合并铁律**（逐条 AI 手动、消歧、删旧）者判不合格。

**类型**：task / decision / preference / emotion / time / context / skill / session
**情绪**：0.0~1.0 数值（默认 0.5），数值越大越重要/强烈；旧词 high=0.8 / medium=0.5 / low=0.2 仍兼容（自动转数值）
**场景与活动时间**：`--scene` 归组（如"教学课后反馈"），`--activity-start/--activity-end` 记段段时间（如旅行 2025-05-01 ~ 05-10）。事件性记忆（time 类型）建议标注。

## 会话桥接（resume，贾维斯块③）

跨会话上下文连续——新会话知上次讲了什么、有什么未竟。**此乃自动决策链之一环：时机到 AI 自发执行，不待用户令**（总纲见 yishi-instructions.md「自动决策链」）。

```bash
# 会话开始（对话启始时与 recall 并用）：
python3 $YISHI resume
# → 输出：上次会话存档（type=session 最新 1 条全文）+ 未完成任务（blocked→in_progress→pending）

# 会话结束（归档后必做）：
python3 $YISHI resume --save "本轮要点：做了什么+关键决策+未竟事项" --title "短标题"
```

**任务状态**（task 类型记忆，metadata.status）：
```bash
... store --type task --keywords "..." --emotion 0.4 "任务描述"        # 默认 pending
... update --id <任务ID> --status in_progress   # 开工
... update --id <任务ID> --status done          # 完工（resume 不再列出）
... update --id <任务ID> --status blocked       # 受阻（resume 置顶列出）
```
状态四值：`pending`（待办 🕐）/ `in_progress`（进行 🔄）/ `done`（完 ✅）/ `blocked`（阻 ⛔）。

## 知识图谱（link，贾维斯块⑤）

记忆间非树型关系用显式链接。树（--parent）表从属；link 表语义关系（因果/引用/矛盾/延伸）。

```bash
# 建立双向关系（存一条，两端 recall 皆可见）：
python3 $YISHI link --source <ID甲> --target <ID乙> --rel-type causes --note "此决策催生此任务"

# 关系四型：
#   causes      ⚡因果 —— 甲导致乙（决策→任务、事故→教训）
#   references  📎引用 —— 甲引用乙（报告→数据源）
#   contradicts ⚔️矛盾 —— 甲与乙矛盾（发现即辨取舍，勿并存自相矛盾）
#   extends     🌱延伸 —— 甲延伸乙（方案 v2 → 方案 v1）

# recall 命中任一端，输出行如：🔗 关联: ⚡因果→标题（注记）
# 顺藤摸瓜：recall ... --expand 展开关联记忆全文

# 删关系：
python3 $YISHI unlink --rel-id <关系ID>
python3 $YISHI unlink --source <ID甲>            # 按源删全部
python3 $YISHI unlink --source A --rel-type contradicts
```

store 时相似 ≥阈值者仍自动建语义关联（score=语义值）；link 建者为手动关系（manual=true, score=1.0），recall 关联行优先显示。

## 自动技能习得（贾维斯块④）

任务完成必自问"此事可否复用"——凡有可复用路径即存技能卡：
```bash
python3 $YISHI store --type skill \
  --skill-name "技能名" --skill-summary "一句话概括" \
  --skill-path "可执行路径/调用方式" --skill-strategy "步骤" \
  --skill-triggers "触发词1,触发词2" \
  --keywords "..." --emotion 0.3 "技能详情全文"
```
- **--skill-path 必填**——无路径 AI 无法定位工具，技能形同虚设。
- **同名查重**：store 自动检测同名技能并打印已有版本（🆔+v版本号+摘要）→ 用 `--merge-ids "<旧ID>" --skill-version <递增>` 合并升级，勿重复造轮。
- **失败亦学**：教训挂技能子节点（`--parent <技能ID>`），必要处写 --skill-avoid 禁忌。
- **recall 触发**：查询词命中 --skill-triggers 时，技能卡自动浮出（⚡触发标记），按卡执行。

**检索命令（新参数）：**
```bash
# 纯关键词快速检索（不加载 embedding 模型，省时）
... recall "关键词" --no-embed

# 注入预算控制（防长记忆爆量）
... recall "关键词" --max-chars-per-item 100 --max-total-chars 600
```
默认已混合检索：BM25 关键词 + 向量语义双路 RRF 融合，人名/专名/代码标识符检索更准。

## 决策前置检索

**凡做决策或提问之前，必先查询记忆。** 无论大小决定——拟建议、择方案、答问题——皆先 `recall` 检索相关记忆，确认有无既有决策、偏好、约定可循：
```bash
MEMO_DIR=~/.local/share/yishi/data python3 ~/.local/share/yishi/scripts/memory_core.py recall "决策主题关键词" --limit 3
```
