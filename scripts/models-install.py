#!/usr/bin/env python3
"""忆时 bge-base-zh-v1.5 模型下载器（幂等，锁防并发，原子写）。

目标：{YISHI_DATA_DIR 或 ~/.local/share/yishi}/models/bge-base-zh-v1.5/
  - onnx/model.onnx（~400MB，bge 768 维，中文语义检索）
  - config.json tokenizer.json special_tokens_map.json tokenizer_config.json vocab.txt

源：hf-mirror（Xenova/bge-base-zh-v1.5），urllib 内建下载（免 curl 依赖，Windows PowerShell/cmd 皆可），失败重试 4 次。
幂等：model.onnx 已存在且大于 100MB 则跳过；并发：锁文件防重复下载。
"""
import os
import sys
import tempfile
from pathlib import Path

# 2026-08-25 与 memory_core.py 统一：全英文 ~/.local/share/yishi（跨平台，Windows 中文路径易乱码）
DATA_BASE = Path(
    os.environ.get("YISHI_DATA_DIR") or str(Path.home() / ".local" / "share" / "yishi")
)
MODEL_DIR = DATA_BASE / "models" / "bge-base-zh-v1.5"
ONNX_DIR = MODEL_DIR / "onnx"
ONNX_FILE = ONNX_DIR / "model.onnx"
FILES = [
    "config.json",
    "tokenizer.json",
    "special_tokens_map.json",
    "tokenizer_config.json",
    "vocab.txt",
]
MIRROR = "https://hf-mirror.com/Xenova/bge-base-zh-v1.5/resolve/main"
LOCK = Path(tempfile.gettempdir()) / "yishi-models-install.lock"
# 模型 ~400MB；小于 100MB 判为残缺（错误页/中断），不认可。
MIN_ONNX_BYTES = 100 * 1024 * 1024


def _pid_alive(pid: int) -> bool:
    """探测进程存活（SIGTERM/kill -9 死后锁须可复用）。"""
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _lock() -> bool:
    if LOCK.exists():
        try:
            old = int(LOCK.read_text().strip())
        except (ValueError, OSError):
            old = None
        if old is not None and _pid_alive(old):
            return False  # 真在下载（apply spawn / 手动并发）
        # 过期锁（进程已死，SIGTERM 等致 finally 未执行）——清除重获
        try:
            LOCK.unlink()
        except OSError:
            return False
    try:
        LOCK.write_text(str(os.getpid()))
        return True
    except OSError:
        return False


def _unlock() -> None:
    try:
        LOCK.unlink()
    except FileNotFoundError:
        pass


def _fetch(url: str, dest: Path) -> None:
    """urllib 下载（内建，免 curl 依赖——PowerShell 5.1 无 curl.exe、cmd 亦未必有）。"""
    import urllib.request
    print(f"↓ {dest.name} ← {url}")
    last_err = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=120) as resp, open(dest, "wb") as out:
                while True:
                    chunk = resp.read(1 << 16)
                    if not chunk:
                        break
                    out.write(chunk)
            if dest.stat().st_size > 0:
                return
            last_err = RuntimeError("下载为空")
        except Exception as e:  # noqa: BLE001
            last_err = e
        print(f"  ⚠️ 第 {attempt + 1} 次失败: {last_err}，重试……", file=sys.stderr)
    raise RuntimeError(f"下载失败: {url} ({last_err})")


def main() -> int:
    if ONNX_FILE.exists() and ONNX_FILE.stat().st_size > MIN_ONNX_BYTES:
        print(f"✅ 模型已在: {ONNX_FILE}")
        return 0
    if not _lock():
        print("⏳ 已有下载进程在跑（锁存在），跳过。", file=sys.stderr)
        return 0
    try:
        ONNX_DIR.mkdir(parents=True, exist_ok=True)
        print(f"下载 bge-base-zh-v1.5（~400MB，hf-mirror）→ {MODEL_DIR}")
        part = ONNX_DIR / "model.onnx.part"
        _fetch(f"{MIRROR}/onnx/model.onnx", part)
        if part.stat().st_size < MIN_ONNX_BYTES:
            part.unlink(missing_ok=True)
            raise RuntimeError("model.onnx 过小，下载不完整")
        part.rename(ONNX_FILE)
        for f in FILES:
            _fetch(f"{MIRROR}/{f}", MODEL_DIR / f)
        print(f"✅ 模型安装完成: {MODEL_DIR}")
        return 0
    except Exception as e:  # noqa: BLE001
        print(f"❌ 模型下载失败: {e}", file=sys.stderr)
        return 1
    finally:
        _unlock()


if __name__ == "__main__":
    sys.exit(main())