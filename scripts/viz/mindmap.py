#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""忆时 · 记忆脑图生成器

将全部记忆绘制为交互式脑图（径向树），方便查看记忆全貌。

用法：
  python3 mindmap.py                       # 导出数据 → 生成脑图 → 打开
  python3 mindmap.py -o /path/out.html     # 指定输出路径
  python3 mindmap.py --no-open             # 生成但不打开
  python3 mindmap.py --data x.json         # 复用已有导出 JSON

依赖：同目录 mindmap_template.html；上一层 memory_core.py。
环境：须设 MEMO_DIR（忆时铁律）。
"""
import json, os, re, subprocess, sys, argparse, tempfile
from pathlib import Path

VIZ_DIR = Path(__file__).resolve().parent
CORE = VIZ_DIR.parent / "memory_core.py"
TPL = VIZ_DIR / "mindmap_template.html"
JSMIND = VIZ_DIR / "jsmind"  # vendored jsMind 库
JSMIND_JS = JSMIND / "jsmind.js"
JSMIND_DRAG = JSMIND / "jsmind.draggable-node.js"
JSMIND_CSS = JSMIND / "jsmind.css"
LOCAL_BASE = Path.home() / ".local" / "share" / "忆时"
DATA_DIR = os.environ.get("MEMO_DIR") or os.environ.get("YISHI_DATA_DIR") or str(LOCAL_BASE / "data")


def _inline_lib():
    """读取 vendored jsMind 库内容，拼为可内嵌单文件字符串。"""
    css = JSMIND_CSS.read_text(encoding="utf-8") if JSMIND_CSS.exists() else ""
    js = JSMIND_JS.read_text(encoding="utf-8") if JSMIND_JS.exists() else ""
    drag = JSMIND_DRAG.read_text(encoding="utf-8") if JSMIND_DRAG.exists() else ""
    return css, js + "\n" + drag

# 主题聚类规则（与 viz.py 一致，顺序优先，首中即归）
TOPICS = [
    ("纸焰小说", ["纸焰", "沈以南", "颜书瑶", "武戏", "爽点", "红痕", "晶核", "关雎", "老刘", "插图prompt"]),
    ("教学学生", ["备课", "课件", "袁雨", "郭瑾萱", "李铎怡", "李多翊", "张梓爱", "陈韵西", "杨柠瑞",
                  "赵柯豪", "课后反馈", "作业", "出题", "命题", "Scratch", "星火征途", "合卷", "重做闭环", "组卷", "错题"]),
    ("GESP考级", ["GESP", "考级", "真题", "大纲", "CSP", "STL", "等级考试"]),
    ("灵逸OJ", ["灵逸", "01oj", "lingyi-oj", "hustoj", "判题", "MMORPG", "域系统", "OJ", "judge", "Monaco", "Vditor", "RBAC"]),
    ("数学讲义", ["组合数学", "typst", "讲义", "加法原理", "乘法原理", "信竞数学", "竞赛编程", "排列组合", "Pólya", "排列", "组合"]),
    ("技能开发", ["技能", "搬题姬", "图片姬", "笔痕", "WebSketch", "ClawHub", "skill", "析题", "发布"]),
    ("系统运维", ["openKylin", "Manjaro", "内核", "音频", "wayland", "Wayland", "死机", "VLC", "微信", "ntfs",
                  "NTFS", "fstab", "GRUB", "KDE", "pkexec", "sudo", "挂载", "驱动", "dphome", "系统配置"]),
    ("工程配置", ["OpenClacky", "七决策", "opencode", "OpenCode", "模型", "DeepSeek", "SenseNova", "供应商", "config", "zen"]),
    ("忆时系统", ["忆时", "记忆梳理", "consolidat", "记忆"]),
]

TYPE_COLORS = {
    "decision": "#FF6B35", "task": "#F7C948", "preference": "#2EC4B6",
    "emotion": "#E07A5F", "time": "#81B29A", "context": "#3D405B", "skill": "#9B5DE5",
}
TYPE_EMOJIS = {
    "decision": "⚖️", "task": "📋", "preference": "⭐", "emotion": "💜",
    "time": "⏰", "context": "📌", "skill": "🔧",
}
TYPE_NAMES = {
    "decision": "决策", "task": "任务", "preference": "偏好", "emotion": "情绪",
    "time": "时间", "context": "上下文", "skill": "技能",
}

def _norm_emo(val):
    if val is None: return 0.5
    s = str(val).strip().lower()
    m = {"extreme": 1.0, "high": 0.8, "medium": 0.5, "low": 0.2}
    if s in m: return m[s]
    try: return max(0.0, min(1.0, float(s)))
    except ValueError: return 0.5

def classify(kw):
    if not kw: return "其他"
    for name, words in TOPICS:
        for w in words:
            if w in kw:
                return name
    return "其他"

def summarize(content, limit=60):
    c = re.sub(r"\s+", " ", (content or "").strip())
    return c if len(c) <= limit else c[:limit] + "…"

def export_json(tmp):
    env = dict(os.environ, MEMO_DIR=DATA_DIR)
    r = subprocess.run([sys.executable, str(CORE), "export", "--format", "json", "--output", str(tmp)],
                       capture_output=True, text=True, env=env)
    if r.returncode != 0:
        raise RuntimeError(f"导出失败: {r.stderr.strip() or r.stdout.strip()}")

def build_mindmap(data, out):
    memories = data.get("memories", [])
    records = []
    for m in memories:
        md = m.get("metadata", {})
        kw = md.get("keywords", "") or ""
        records.append({
            "id": m["id"],
            "type": md.get("type", "context"),
            "emotion": _norm_emo(md.get("emotion")),
            "date": md.get("created_date", "") or (md.get("created_at", "") or "")[:10],
            "keywords": [k for k in kw.split(",") if k][:8],
            "kw_raw": kw,
            "freq": int(md.get("frequency", 1) or 1),
            "recall": int(md.get("recall_count", 0) or 0),
            "topic": classify(kw),
            "c": summarize(m.get("content", "")),
        })

    # 构建 jsMind 脑图（node_tree 格式，渐进式披露）
    # 根: 忆时记忆 → 类型 → 主题 → 记忆叶子
    # 初始仅展开类型一层，主题/记忆默认收起（点展开，省 token）

    # 先按类型分组
    type_groups = {}
    for r in records:
        t = r["type"]
        type_groups.setdefault(t, []).append(r)

    root_children = []
    for t in ["decision", "task", "preference", "context", "skill", "emotion", "time"]:
        mems = type_groups.get(t, [])
        if not mems:
            continue
        # 按主题分组
        topic_groups = {}
        for m in mems:
            top = m["topic"]
            topic_groups.setdefault(top, []).append(m)

        type_children = []
        # 无主题（其他）的记忆直接为叶子
        for top, ms in sorted(topic_groups.items(), key=lambda x: -len(x[1])):
            if top == "其他" and len(ms) <= 5:
                for m in ms:
                    type_children.append(jsmind_leaf(m))
            else:
                topic_children = [jsmind_leaf(m) for m in ms]
                topic_children.sort(key=lambda x: -x.get("_emotion_", 0))
                type_children.append({
                    "id": f"topic_{t}_{len(type_children)+1}",  # 用 type_children 当前长度 +1 作唯一序号
                    "topic": f"{top} ({len(ms)})",
                    "expanded": False,  # 主题默认收起（渐进）
                    "data": {"background-color": TYPE_COLORS.get(t, "#999"), "float": "right"},
                    "children": topic_children,
                })

        type_id = f"type_{t}"
        root_children.append({
            "id": type_id,
            "topic": f"{TYPE_EMOJIS.get(t,'')} {TYPE_NAMES.get(t,t)} ({len(mems)})",
            "expanded": False,  # 类型默认收起
            "data": {"background-color": TYPE_COLORS.get(t, "#999")},
            "children": type_children,
        })

    mind = {
        "meta": {"name": "忆时记忆脑图", "author": "fslong", "version": "0.3.0"},
        "format": "node_tree",
        "data": {
            "id": "root",
            "topic": f"忆时记忆 ({len(records)})",
            "expanded": True,  # 根展开显示类型总览
            "children": root_children,
        },
    }

    payload = {
        "mind": mind,
        "total": len(records),
        "export_date": data.get("export_date", ""),
        "type_colors": TYPE_COLORS,
        "type_names": TYPE_NAMES,
        "type_emojis": TYPE_EMOJIS,
    }

    if not TPL.exists():
        raise RuntimeError(f"模板不存在: {TPL}")
    css, js = _inline_lib()
    tpl_html = TPL.read_text(encoding="utf-8")
    # 占位符全部校验
    for ph in ["/*__MINDMAP_DATA__*/", "/*__JSMIND_CSS__*/", "/*__JSMIND_JS__*/"]:
        if ph not in tpl_html:
            raise RuntimeError(f"mindmap_template.html 缺少占位符 {ph}")
    html = tpl_html
    html = html.replace("/*__JSMIND_CSS__*/", css)
    html = html.replace("/*__JSMIND_JS__*/", js)
    html = html.replace("/*__MINDMAP_DATA__*/", json.dumps(payload, ensure_ascii=False))
    out.write_text(html, encoding="utf-8")
    return payload

def jsmind_leaf(m):
    """jsMind 叶子节点：topic=摘要，data 存详情（悬停显示）"""
    topic = (m["c"] or "（空）").replace("<", "&lt;")
    return {
        "id": m["id"],
        "topic": topic,
        "data": {
            "_emotion_": m["emotion"],
            "_date_": m["date"],
            "_keywords_": m["keywords"],
            "_recall_": m["recall"],
            "_type_name_": TYPE_NAMES.get(m["type"], m["type"]),
            "_type_emoji_": TYPE_EMOJIS.get(m["type"], ""),
            "_color_": TYPE_COLORS.get(m["type"], "#999"),
        },
    }

def open_in_browser(path):
    if sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    elif os.name == "nt":
        os.startfile(str(path))
    else:
        subprocess.Popen(["xdg-open", str(path)])

def main():
    ap = argparse.ArgumentParser(description="忆时记忆脑图")
    ap.add_argument("-o", "--output", default=str(Path.home() / "Desktop" / "忆时记忆脑图.html"))
    ap.add_argument("--no-open", action="store_true", help="生成后不自动打开")
    ap.add_argument("--data", default=None, help="复用已有导出JSON文件")
    args = ap.parse_args()

    if args.data:
        data = json.load(open(args.data, encoding="utf-8"))
    else:
        tmp = Path(tempfile.gettempdir()) / "yishi_all.json"
        export_json(tmp)
        data = json.load(open(tmp, encoding="utf-8"))

    payload = build_mindmap(data, Path(args.output))
    print(f"✅ 记忆脑图已生成: {args.output}")
    print(f"   共 {payload['total']} 条记忆 · 类型 {len(payload['type_colors'])} 类")
    if not args.no_open:
        open_in_browser(Path(args.output))
        print("   已在浏览器打开")

if __name__ == "__main__":
    main()