#!/usr/bin/env python3
"""
技能-正文一致性巡检（F10，半自动）

从 docs/00-项目总览/事实断言清单.md 提取"断言中可 grep 的关键事实"，
在 AI_Skill 对应技能与 docs 正文中双端比对，发现漂移进报告。
机制：手动 grep 机器核对的自动化替代（自我验证修正机制 §2 L2 层）。

用法：
    python scripts/assertion_check.py            # 全量巡检
    python scripts/assertion_check.py --fix-report  # 输出 Markdown 报告到 Testing/output/
"""

import re
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECKS = [
    # (断言ID, 技能文件, 技能侧必须包含, 正文目录(可多个), 正文侧必须包含)
    ("A1", "AI_Skill/skills/redis-ecosystem-versions/SKILL.md", ["8.10"],
     ["docs/03-Redis组件/03.05-Redis生态与版本演进/README.md"], ["8.4"]),
    ("A3", "AI_Skill/skills/redis-ecosystem-versions/SKILL.md", ["9.1"],
     ["docs/03-Redis组件/03.05-Redis生态与版本演进/README.md"], ["Valkey"]),
    ("A5", "AI_Skill/skills/os-kernel-cache/SKILL.md", ["6.1"],
     ["docs/02-系统实现/02.04-现代内核缓存机制/README.md"], ["MGLRU"]),
    ("C2", "AI_Skill/skills/cache-data-management/SKILL.md", ["65"],
     ["docs/07-运维与部署/07.05-集群管理/07.05.04-集群容量规划.md"], ["65,359"]),
    ("B1", "AI_Skill/skills/cache-algorithms-advanced/SKILL.md", ["SOSP", "NSDI"],
     ["docs/01-理论基础/01.02-高级替换算法/01.02.10-S3-FIFO与SIEVE算法.md"], ["SOSP", "NSDI"]),
]


def read(p):
    try:
        return (ROOT / p).read_text(encoding="utf-8")
    except OSError:
        return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix-report", action="store_true")
    args = ap.parse_args()

    results = []
    for check_id, skill_rel, skill_needles, doc_rels, doc_needles in CHECKS:
        skill_txt = read(skill_rel)
        doc_txt = "\n".join(read(d) for d in doc_rels)
        missing_skill = [n for n in skill_needles if n not in skill_txt]
        missing_doc = [n for n in doc_needles if n not in doc_txt]
        status = "PASS" if not (missing_skill or missing_doc) else "DRIFT"
        results.append((check_id, status, missing_skill, missing_doc))

    drift = [r for r in results if r[1] == "DRIFT"]
    for cid, st, ms, md in results:
        line = f"[{st}] {cid}"
        if ms:
            line += f" 技能缺: {ms}"
        if md:
            line += f" 正文缺: {md}"
        print(line)

    if args.fix_report:
        out = ROOT / "Testing" / "output"
        out.mkdir(parents=True, exist_ok=True)
        md = ["# 技能-正文一致性巡检报告\n"]
        for cid, st, ms, mdd in results:
            md.append(f"- **{cid}** {st}" + (f"：技能缺 {ms} / 正文缺 {mdd}" if st == "DRIFT" else ""))
        (out / "assertion_check.md").write_text("\n".join(md), encoding="utf-8")
        print(f"报告已写: {out / 'assertion_check.md'}")

    print(f"\n结果: {len(results) - len(drift)} PASS / {len(drift)} DRIFT")
    return 1 if drift else 0


if __name__ == "__main__":
    raise SystemExit(main())
