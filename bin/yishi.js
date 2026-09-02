#!/usr/bin/env node
// yishi CLI — 自动同步脚本 + 验环境，转发到 memory_core.py
// 用法: yishi <subcommand> [args...]
// 等价于: python3 <yishi_dir>/scripts/memory_core.py <subcommand> [args...]

import { spawnSync } from "node:child_process";
import { createRequire } from "node:module";
import { existsSync, readFileSync, writeFileSync, mkdirSync, copyFileSync } from "node:fs";
import { homedir, platform } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const pkg = createRequire(import.meta.url)("../package.json");

const YISHI_HOME = join(homedir(), ".local", "share", "yishi");
const SCRIPTS_DIR = join(YISHI_HOME, "scripts");
const MEMO_DIR = join(YISHI_HOME, "data");
const CORE = join(SCRIPTS_DIR, "memory_core.py");
const INSTALL = join(SCRIPTS_DIR, "install.py");

function findPython() {
  const candidates = platform() === "win32" ? ["python", "py -3"] : ["python3", "python"];
  for (const cmd of candidates) {
    const r = spawnSync(cmd, ["--version"], { encoding: "utf8", timeout: 5000 });
    if (r.status === 0) return cmd;
  }
  return null;
}

function syncScripts() {
  const pkgScripts = join(__dirname, "..", "scripts");
  if (!existsSync(pkgScripts)) return false;
  mkdirSync(SCRIPTS_DIR, { recursive: true });
  for (const name of ["memory_core.py", "install.py", "models-install.py", "requirements.txt", "__init__.py"]) {
    const src = join(pkgScripts, name);
    const dst = join(SCRIPTS_DIR, name);
    if (existsSync(src)) {
      copyFileSync(src, dst);
    }
  }
  // viz 目录
  const vizSrc = join(pkgScripts, "viz");
  const vizDst = join(SCRIPTS_DIR, "viz");
  if (existsSync(vizSrc)) {
    mkdirSync(vizDst, { recursive: true });
    for (const f of ["viz.py", "mindmap.py", "profile.py", "d3.min.js", "memory_mindmap_template.html", "memory_panorama_template.html", "profile_template.html", "mindmap_template.html"]) {
      const sf = join(vizSrc, f);
      if (existsSync(sf)) copyFileSync(sf, join(vizDst, f));
    }
  }
  return true;
}

function ensureEnv(python) {
  // 先同步脚本
  syncScripts();
  if (!existsSync(CORE)) {
    console.error("yishi: 找不到 memory_core.py，请重新安装 @fslong/dsh-yishi");
    process.exit(1);
  }
  // 检查环境
  const check = spawnSync(python, [INSTALL, "--check"], {
    encoding: "utf8",
    timeout: 30000,
    env: { ...process.env, MEMO_DIR },
  });
  if (check.status !== 0) {
    console.error("yishi: 环境未就绪，自动修复中...");
    const fix = spawnSync(python, [INSTALL], {
      encoding: "utf8",
      timeout: 120000,
      env: { ...process.env, MEMO_DIR },
    });
    if (fix.status !== 0) {
      console.error("yishi: 环境修复失败，请手动执行: python3 " + INSTALL);
      process.exit(1);
    }
    console.error("yishi: 环境已就绪");
  }
}

function main() {
  const python = findPython();
  if (!python) {
    console.error("yishi: 找不到 Python 3.9+，请先安装 Python");
    process.exit(1);
  }
  // 自动同步 + 验环境
  ensureEnv(python);
  // 转发参数
  const args = process.argv.slice(2);
  if (args.length === 0) {
    const r = spawnSync(python, [CORE, "--help"], { stdio: "inherit", encoding: "utf8" });
    process.exit(r.status ?? 0);
  }
  const result = spawnSync(python, [CORE, ...args], {
    stdio: "inherit",
    encoding: "utf8",
    timeout: 300000,
    env: { ...process.env, MEMO_DIR },
  });
  process.exit(result.status ?? 0);
}

main();