# 模块 10 - 记忆自动梳理

**何时读**：对话启始检查梳理状态，末次梳理距今超过 7 日时；用户输入 `/忆时 梳理` 时。

**每七日一梳理，沉淀精华，去芜存菁。** 此乃对抗"窗口即牢笼"之根本策略——将散落各对话之碎片，聚为结构化知识。

> ⚠️ **合并铁律（2026-08-22 立）**：梳理非"追加索引"，乃"AI 手动合并归旧"。高相关性记忆**必须一条条 AI 手动合并**，消歧矛盾、取最新正确、删旧条目——**严禁靠脚本机械拼接、严禁贪省批量合并**。为何：autostore 去重仅在相似度 ≥90% 时机械拼接内容（`旧。新`），措辞稍异即分家，多日累积出同主题多条且互相矛盾（如"决不可用 sudo"与"sudo 密码 xcxw1314 用 sudo -S"同库并存）。此病根，梳理当治之。

## 追踪梳理时间

以特殊记忆追踪末次梳理时间。每次对话启始，先查：
```bash
MEMO_DIR=~/.local/share/忆时/data python3 ~/.local/share/忆时/scripts/memory_core.py \
  recall "记忆梳理" --type-filter time --limit 1 --min-weight 0.1
```
- **返回末次梳理时间**：有结果则告知用户"上次梳理于 XXXX-XX-XX"；无结果则言"尚无梳理记录"。
- 若无结果，或末次梳理距今超过 7 日 → 触发梳理流程。
- 梳理毕，以 `--type time --emotion 0.5 --keywords "记忆梳理,consolidation"` 存储新时间戳：
  ```bash
  MEMO_DIR=~/.local/share/忆时/data python3 ~/.local/share/忆时/scripts/memory_core.py \
    store "上次记忆梳理时间: YYYY-MM-DD" --type time --emotion 0.5 --keywords "记忆梳理,consolidation"
  ```
- 梳理完成，告知用户"梳理完毕，上次梳理时间已更新"。

## 梳理流程

1. **导出所有记忆**
   ```bash
   MEMO_DIR=~/.local/share/忆时/data python3 ~/.local/share/忆时/scripts/memory_core.py \
     export --format timeline --output /tmp/yishi_export.md
   ```

2. **AI 分析导出内容**——以 AI 原生工具（read/grep）读 `/tmp/yishi_export.md`：
   - 先**聚类高相关组**：同主题/同关键词/同语义之记忆归一组（如同一提权策略、同一工具修复、同一项目进度）。聚不足，不轻下。
   - 再**逐条读全该组每条原文**——不凭摘要印象跳扫，漏一字即失责。

3. **一条条 AI 手动合并**（核心，戒批量、戒脚本拼接）：
   - 每组**只存一条权威合并版**：含【前因】【行为】【后果】三要素（铁律，见 13-retrieval-store），信息须自足——三月后读之犹能独立理解。
   - **消歧矛盾**：同组内互相冲突处，取**最新者正确**（时间戳靠后者为最新认知），旧认知明示淘汰（如"决不可用 sudo"已为"sudo 有密码 xcxw1314、非交互才用 pkexec"所取代）。
   - **舍重**：重复铺垫/旧细节不并入，宁精勿杂。
   - 存合并版（`--force` 跳过自动去重，阻机械拼接）：
     ```bash
     MEMO_DIR=~/.local/share/忆时/data python3 ~/.local/share/忆时/scripts/memory_core.py \
       store "合并版全文" --type preference --emotion 0.7 --keywords "关键词,consolidated" --force
     ```
   - **删旧条目**：合并版存妥、读回确认后，`delete` 掉该组其余被并入之旧记忆（真正的合并，非追加）。`delete --id <ID>` 一条条删。

4. **清理临时文件**：`rm /tmp/yishi_export.md`

## 梳理原则

- **高相关必合并**：同主题/同语义归并，此为铁律。散则留、重复则合、矛盾则消。
- **一手判，勿贪懒**：每条合并均由 AI 手动成书——读全组、判矛盾、写合并、删旧单。不许以脚本`merge`代劳，不许批量一把梭。穷尽加问：这组的矛盾我消了吗？旧条目删干净了吗？合并版自足吗？
- 频率>7日可跳：若用户对话稀疏，7日内无新记忆，则不必空转。
- 情绪高之记忆优先：梳理时，优先关注情绪值 ≥0.7 之条目，此乃用户最在意之事。
- 对比旧梳理：检索已有 `--keywords "consolidated"` 之记忆，比对新增内容，避免重复沉淀。

完成后回复：`"梳理毕。"`
