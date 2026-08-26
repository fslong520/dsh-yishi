#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""忆时环境自愈安装器（跨平台，幂等）。

设计原则：
  - 一律用 sys.executable（当前解释器）调 pip / 子脚本，不硬编码 python3/python——
    谁运行本脚本，就用谁的 pip，Windows（python）与 Linux/macOS（python3）天然兼容。
  - 全流程幂等：已装依赖跳过、已建 data 跳过、已有模型跳过，可反复运行。
  - 分步可单独执行（--deps-only / --init-only / --model-only / --opencode-only），
    AI 自愈时按需调用。

用法：
  python3 install.py                # 全流程：依赖 → 模型 → 初始化 → 验证 → opencode 配置
  python3 install.py --check        # 只检测，缺什么列什么（不安装）
  python3 install.py --deps-only    # 仅装 Python 依赖
  python3 install.py --init-only    # 仅建 data 目录 + 初始化 Chroma
  python3 install.py --model-only   # 仅下载 bge 模型
  python3 install.py --opencode-only  # 仅配置 opencode.json 外挂提示词（幂等合并）
  python3 install.py --verbose      # 全流程 + 打印 pip 详情

退出码：0 全过 / 1 某步失败 / 2 检查发现缺失。
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

MIN_PY = (3, 9)  # chromadb 1.5.x 要求 Python >= 3.9；代码本身 3.8+ 语法足够

LOCAL_BASE = Path(
    os.environ.get("YISHI_DATA_DIR") or str(Path.home() / ".local" / "share" / "yishi")
)
SCRIPT_DIR = Path(__file__).resolve().parent
REQ_FILE = SCRIPT_DIR / "requirements.txt"
CORE = SCRIPT_DIR / "memory_core.py"
MODELS_INSTALL = SCRIPT_DIR / "models-install.py"
DATA_DIR = Path(
    os.environ.get("MEMO_DIR") or os.environ.get("YISHI_DATA_DIR") or str(LOCAL_BASE / "data")
)
MODEL_DIR = LOCAL_BASE / "models" / "bge-base-zh-v1.5" / "onnx" / "model.onnx"


def _py():
    """当前解释器（供 subprocess 复用）。"""
    return sys.executable


def _run(args, **kw):
    """子进程包装：打印命令，透传退出码。"""
    print(f"  $ {' '.join(args)}")
    r = subprocess.run(args, **kw)
    if r.returncode != 0:
        print(f"  ❌ 退出码 {r.returncode}: {' '.join(args)}", file=sys.stderr)
    return r


def check_python():
    """Python 版本门槛。"""
    ok = sys.version_info >= MIN_PY
    print(f"[1/4] Python 版本: {sys.version.split()[0]} "
          f"({'✓' if ok else '✗ 需 ≥ ' + '.'.join(map(str, MIN_PY))})")
    return ok


def check_deps():
    """缺哪些依赖（以 import 试错为准，不数包名）。"""
    missing = []
    for mod in ["chromadb", "jieba", "onnxruntime", "tokenizers", "numpy"]:
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    if missing:
        print(f"[2/4] 依赖: ✗ 缺 {', '.join(missing)}")
    else:
        print(f"[2/4] 依赖: ✓ 全齐")
    return missing


def install_deps(verbose=False):
    """pip 安装 requirements.txt。"""
    missing = check_deps()
    if not missing:
        return True
    if not REQ_FILE.exists():
        print(f"  ❌ 找不到 {REQ_FILE}", file=sys.stderr)
        return False
    print(f"  ↓ 安装依赖（{REQ_FILE.name}）……")
    quiet = [] if verbose else ["--quiet", "--disable-pip-version-check"]
    r = _run([_py(), "-m", "pip", "install"] + quiet + ["-r", str(REQ_FILE)])
    return r.returncode == 0


def check_data():
    """data 目录与 Chroma 初始化。"""
    exists = (DATA_DIR / "chroma.sqlite3").exists() or (DATA_DIR / "chroma.sqlite").exists()
    print(f"[3/4] 数据目录: {DATA_DIR} {'✓' if exists else '✗ 未初始化'}")
    return exists


def init_data():
    """mkdir + memory_core.py init。"""
    if check_data():
        print("  ✓ 已初始化，跳过")
        return True
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"  ↓ 初始化 Chroma（{CORE.name} init）……")
    r = _run([_py(), str(CORE), "init"])
    return r.returncode == 0


def check_model():
    """bge 模型 onnx 是否就位（>100MB 判完整）。"""
    ok = MODEL_DIR.exists() and MODEL_DIR.stat().st_size > 100 * 1024 * 1024
    print(f"[4/4] 模型 bge-base-zh-v1.5: {'✓' if ok else '✗ 缺失'}")
    return ok


def install_model():
    """调 models-install.py（幂等，锁防并发）。"""
    if check_model():
        print("  ✓ 模型已在，跳过")
        return True
    if not MODELS_INSTALL.exists():
        print(f"  ❌ 找不到 {MODELS_INSTALL}", file=sys.stderr)
        return False
    print(f"  ↓ 下载 bge 模型（~400MB，hf-mirror；首次需等待）……")
    r = _run([_py(), str(MODELS_INSTALL)])
    return r.returncode == 0


def verify():
    """真实验证：recall 一记空查，能跑通即环境可作。"""
    print("  ↓ 验证：recall 空查……")
    r = subprocess.run(
        [_py(), str(CORE), "recall", "环境自愈验证", "--limit", "1"],
        capture_output=True, text=True,
    )
    if r.returncode == 0:
        print(f"  ✓ 验证通过: {r.stdout.strip().splitlines()[-1] if r.stdout.strip() else 'recall ok'}")
        return True
    print(f"  ❌ 验证失败 rc={r.returncode}", file=sys.stderr)
    print(r.stderr[-800:], file=sys.stderr)
    return False


# ── opencode.json 外挂提示词配置（幂等合并）──
# opencode 需要 instructions 指向 yishi-instructions.md 才自动检索/存储。
# 本函数自动检测 ~/.config/opencode/opencode.json(.c)，合并 instructions 数组，
# 不破坏用户已有配置；已有忆时路径则跳过。Windows 路径同 ~/.config/opencode。
OPCODE_DIR = Path.home() / ".config" / "opencode"
INST_PATH = str(Path("~") / ".local" / "share" / "yishi" / "docs" / "yishi-instructions.md")


def _find_opencode_file():
    """返回现有 opencode 配置文件路径；无则 None。"""
    for name in ("opencode.json", "opencode.jsonc"):
        p = OPCODE_DIR / name
        if p.exists():
            return p
    return None


def check_opencode():
    """检测：instructions 是否已含忆时路径。"""
    f = _find_opencode_file()
    if f is None:
        print("[5/5] opencode 配置: ✗ 无配置文件（install.py 全流程会自动创建）")
        return False
    try:
        text = f.read_text(encoding="utf-8")
    except OSError:
        print(f"[5/5] opencode 配置: ✗ 读取失败 {f}")
        return False
    ok = "~/.local/share/yishi" in text and "yishi-instructions.md" in text
    print(f"[5/5] opencode 配置: {f.name} {'✓ 已含忆时指令' if ok else '✗ 未含（install.py 会自动合并）'}")
    return ok


def _jsonc_merge_instructions(text):
    """把忆时路径并入 instructions 数组（JSONC 兼容：纯文本正则，不解析 JSON）。

    返回 (新文本, 是否改动)。处理三种形态：
      - 已有 "instructions": [...] 数组 → 数组内追加（去重）
      - 无 instructions 字段 → 在首个 { 后插入字段
    """
    inst = json.dumps(INST_PATH, ensure_ascii=False)
    if "~/.local/share/yishi" in text and "yishi-instructions.md" in text:
        return text, False
    m = re.search(r'("instructions"\s*:\s*\[)', text)
    if m:
        # 找数组结束的 ]（简单起见：该行或后续最近一个 ]）
        start = m.end()
        end = text.find("]", start)
        if end == -1:
            return text, False
        inside = text[start:end]
        if inside.strip():
            text = text[:start] + inside.rstrip() + ", " + inst + text[end:]
        else:
            text = text[:start] + inst + text[end:]
        return text, True
    # 无 instructions 字段：首个 { 后插入
    pos = text.find("{")
    if pos == -1:
        return text, False
    text = text[: pos + 1] + "\n  \"instructions\": [" + inst + "]," + text[pos + 1:]
    return text, True


def setup_opencode():
    """幂等合并 opencode.json(.c) 之 instructions。"""
    if check_opencode():
        return True
    OPCODE_DIR.mkdir(parents=True, exist_ok=True)
    f = _find_opencode_file()
    target = f if f is not None else OPCODE_DIR / "opencode.json"
    if f is None:
        body = "{\n  \"instructions\": [" + json.dumps(INST_PATH, ensure_ascii=False) + "]\n}\n"
        try:
            target.write_text(body, encoding="utf-8")
            print(f"  ✓ 已创建 {target}（instructions 指向 yishi-instructions.md）")
            return True
        except OSError as e:
            print(f"  ❌ 创建失败 {target}: {e}", file=sys.stderr)
            return False
    try:
        text = f.read_text(encoding="utf-8")
    except OSError as e:
        print(f"  ❌ 读取失败 {f}: {e}", file=sys.stderr)
        return False
    new_text, changed = _jsonc_merge_instructions(text)
    if not changed:
        print(f"  ✓ 无需改动 {f}")
        return True
    try:
        f.write_text(new_text, encoding="utf-8")
        print(f"  ✓ 已合并 instructions → {f}")
        return True
    except OSError as e:
        print(f"  ❌ 写入失败 {f}: {e}", file=sys.stderr)
        return False


def main():
    args = [a for a in sys.argv[1:]]
    mode_check = "--check" in args
    deps_only = "--deps-only" in args
    init_only = "--init-only" in args
    model_only = "--model-only" in args
    opencode_only = "--opencode-only" in args
    verbose = "--verbose" in args

    # ── 检测（check 模式到此为止）──
    py_ok = check_python()
    if not py_ok:
        print("✗ Python 版本过低。请安装 Python 3.9+ 后重试。", file=sys.stderr)
        return 1 if not mode_check else 2

    if mode_check:
        missing = check_deps()
        data_ok = check_data()
        model_ok = check_model()
        oc_ok = check_opencode()
        if not missing and data_ok and model_ok and oc_ok:
            print("\n✓ 环境齐备，可直接使用。")
            return 0
        print("\n✗ 缺失项见上。修复：python3 install.py（Windows: python install.py）")
        return 2

    # ── 修复（顺序有讲究：init 会加载 embedding 模型，故模型必须先于 init）──
    ok = True
    if not deps_only and not init_only and not opencode_only:
        ok &= install_deps(verbose)
    if not model_only and not init_only and not opencode_only:
        ok &= install_model()
    if not deps_only and not model_only and not opencode_only:
        ok &= init_data()
    if not opencode_only:
        if ok and not deps_only and not model_only:
            ok &= verify()
        ok &= setup_opencode()
    else:
        ok &= setup_opencode()

    print("\n" + ("✓ 环境就绪。" if ok else "✗ 有步骤失败，见上方错误。"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
