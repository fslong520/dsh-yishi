#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""忆时环境自愈安装器（跨平台，幂等）。

设计原则：
  - 一律用 sys.executable（当前解释器）调 pip / 子脚本，不硬编码 python3/python——
    谁运行本脚本，就用谁的 pip，Windows（python）与 Linux/macOS（python3）天然兼容。
  - 全流程幂等：已装依赖跳过、已建 data 跳过、已有模型跳过，可反复运行。
  - 分步可单独执行（--deps-only / --init-only / --model-only），AI 自愈时按需调用。

用法：
  python3 install.py                # 全流程：依赖 → 初始化 → 模型 → 验证
  python3 install.py --check        # 只检测，缺什么列什么（不安装）
  python3 install.py --deps-only    # 仅装 Python 依赖
  python3 install.py --init-only    # 仅建 data 目录 + 初始化 Chroma
  python3 install.py --model-only   # 仅下载 bge 模型
  python3 install.py --verbose      # 全流程 + 打印 pip 详情

退出码：0 全过 / 1 某步失败 / 2 检查发现缺失。
"""
import os
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


def main():
    args = [a for a in sys.argv[1:]]
    mode_check = "--check" in args
    deps_only = "--deps-only" in args
    init_only = "--init-only" in args
    model_only = "--model-only" in args
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
        if not missing and data_ok and model_ok:
            print("\n✓ 环境齐备，可直接使用。")
            return 0
        print("\n✗ 缺失项见上。修复：python3 install.py（Windows: python install.py）")
        return 2

    # ── 修复（顺序有讲究：init 会加载 embedding 模型，故模型必须先于 init）──
    ok = True
    if not deps_only and not init_only:
        ok &= install_deps(verbose)
    if not model_only and not init_only:
        ok &= install_model()
    if not deps_only and not model_only:
        ok &= init_data()
    if ok and not deps_only and not model_only:
        ok &= verify()

    print("\n" + ("✓ 环境就绪。" if ok else "✗ 有步骤失败，见上方错误。"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
