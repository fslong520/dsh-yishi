# 模块 08 - 模型安装、配置与参考

**何时读**：首次安装/切换 embedding 模型、维度重建、配置 opencode.json 外挂提示词、排查"AI不自动检索"问题时。日常无此场景不读。

## 模型安装

本技能使用 **bge-base-zh-v1.5**（BAAI 中文语义模型，768 维，~400MB）——中文记忆检索质量远超英文模型 MiniLM。引擎检测 `~/.local/share/yishi/models/bge-base-zh-v1.5/onnx/model.onnx`，缺失即报错退出，**无回退**（MiniLM 384 维与 bge 768 维数据不兼容，曾致维度冲突）。

**bge-base-zh-v1.5 安装**（模型放运行时目录，技能更新不覆盖）：

```bash
mkdir -p ~/.local/share/yishi/models/bge-base-zh-v1.5/onnx
# 自 hf-mirror 下载（或浏览器下载后放入）
curl -sL -o ~/.local/share/yishi/models/bge-base-zh-v1.5/onnx/model.onnx \
  https://hf-mirror.com/Xenova/bge-base-zh-v1.5/resolve/main/onnx/model.onnx
cd ~/.local/share/yishi/models/bge-base-zh-v1.5
for f in config.json tokenizer.json special_tokens_map.json tokenizer_config.json vocab.txt; do
  curl -sL -o "$f" "https://hf-mirror.com/Xenova/bge-base-zh-v1.5/resolve/main/$f"
done
```

> ⚠️ **注意**：运行时模型与数据统一存 `~/.local/share/yishi/`（LOCAL_BASE），**不写入 `~/.cache/chroma/`**，亦不存技能目录（技能更新会覆盖）。

## 外挂提示词（自动配置，验证方法）

本技能依赖 OpenCode 的 `instructions` 配置才能完整生效（DSH 插件已自动注入，无需配置）。
为保障 opencode 双栖用户，`install.py` 全流程与插件 apply 均已自动合并 `~/.config/opencode/opencode.json`（或 `.jsonc`）的 `instructions` 数组，指向 `~/.local/share/yishi/docs/yishi-instructions.md`，**无需手动编辑**。

**验证方法：**
```bash
python3 ~/.local/share/yishi/scripts/install.py --check
# 输出应含「opencode 配置: ✓ 已含忆时指令」
```

**手动配置（仅需确认时）：**
1. 编辑全局配置文件 `~/.config/opencode/opencode.json`（或 `.jsonc`）
2. 确认 `instructions` 字段包含以下路径（自动配置已代劳，验证即可）：
```json
{
  "instructions": [
    "~/.local/share/yishi/docs/yishi-instructions.md"
  ]
}
```
3. 重启 OpenCode 使配置生效

**配置后 AI 将自动：**
- 每次对话前检索记忆系统
- 用户说"记住"时自动存储记忆
- 话题关联时主动涌现历史记忆
- 对话结束时自动归档重点

**未配置则：**
- 技能仍可手动调用命令
- 但不会自动检索/存储记忆
- 不会主动联想和闪回

## 运行环境

- Python: 3.9+（Windows 用 `python`，Linux/macOS 用 `python3`）
- 依赖: chromadb>=1.5.4、jieba、onnxruntime、tokenizers、numpy（见 `scripts/requirements.txt`）
- 脚本: `scripts/memory_core.py`
- 数据: `data/` (ChromaDB PersistentClient 自动创建)

### 依赖安装（首次必做，AI 自愈亦走此路）

脚本顶层 import chromadb/jieba 失败时已打印指引；亦可主动安装：

```bash
# 一键全流程（依赖 + 初始化 + 模型，幂等，推荐）
python3 ~/.local/share/yishi/scripts/install.py
# Windows PowerShell（无 python3 用 python；$env:USERPROFILE 替 ~）
python $env:USERPROFILE\.local\share\yishi\scripts\install.py
# Windows cmd.exe
python %USERPROFILE%\.local\share\yishi\scripts\install.py

# 只装 Python 依赖
python3 -m pip install -r ~/.local/share/yishi/scripts/requirements.txt
# Windows PowerShell / cmd.exe
python -m pip install -r $env:USERPROFILE\.local\share\yishi\scripts\requirements.txt
python -m pip install -r %USERPROFILE%\.local\share\yishi\scripts\requirements.txt
```

> **解释器选择**：脚本一律以 `sys.executable`（当前解释器）调 pip/子脚本，不硬编码 python3/python——Windows 只有 `python` 时，用 `python` 跑 install.py 即可，无需降级 Python、无需安装 python3 别名。
> **PowerShell 三忌**：①`%USERPROFILE%` 是 cmd 语法，PS 中不展开——用 `$env:USERPROFILE`，接子路径写 `${env:USERPROFILE}\.local\...`（花括号防 `.local` 被并入变量名）；②`export VAR=...` 是 bash 语法，PS 用 `$env:VAR = "..."`；③`python3` 常不存在，用 `python`。
