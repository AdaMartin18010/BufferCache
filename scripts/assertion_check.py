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
    # 扩充：覆盖全部技能的关键可 grep 事实（2026-11-17 首次全量）
    ("D1", "AI_Skill/skills/redis-data-structures/SKILL.md", ["44"],
     ["docs/03-Redis组件/03.01-核心数据结构/03.01.13-序列化编码与内存布局权衡.md"], ["44"]),
    ("D2", "AI_Skill/skills/redis-persistence-ha/SKILL.md", ["16384"],
     ["docs/03-Redis组件/03.03-高可用架构/03.03.03-Cluster集群模式.md"], ["16384"]),
    ("D3", "AI_Skill/skills/distributed-architecture/SKILL.md", ["2014"],
     ["docs/08-分布式架构/08.01-分布式一致性/08.01.01-Raft协议实践.md"], ["2014"]),
    ("D4", "AI_Skill/skills/cache-algorithms-fundamentals/SKILL.md", ["2003"],
     ["docs/01-理论基础/01.01-基础替换算法/01.01.01-LRU算法原理与实现.md"], ["2003"]),
    ("D5", "AI_Skill/skills/learning-driven-cache/SKILL.md", ["FAST 2025"],
     ["docs/01-理论基础/01.04-学习驱动缓存算法/README.md"], ["3L-Cache"]),
    ("D6", "AI_Skill/skills/llm-kv-cache/SKILL.md", ["85.5"],
     ["docs/04-架构设计/04.03-行业应用场景/04.03.15-大模型推理缓存架构.md"], ["85.5"]),
    ("D7", "AI_Skill/skills/os-kernel-cache/SKILL.md", ["5.16"],
     ["docs/02-系统实现/02.04-现代内核缓存机制/README.md"], ["5.16"]),
    ("D8", "AI_Skill/skills/cloud-native-cache/SKILL.md", ["Valkey"],
     ["docs/04-架构设计/04.03-行业应用场景/04.03.16-云原生缓存趋势与实践.md"], ["Valkey"]),
    ("D9", "AI_Skill/skills/elastic-selfhealing/SKILL.md", ["KEDA"],
     ["docs/07-运维与部署/07.09-弹性伸缩与自愈/07.09.01-自动伸缩实践.md"], ["KEDA"]),
    ("D10", "AI_Skill/skills/cache-security/SKILL.md", ["2014"],
     ["docs/04-架构设计/04.02-缓存安全/README.md"], ["2014"]),
    ("D11", "AI_Skill/skills/db-cloud-cache/SKILL.md", ["Heat Map"],
     ["docs/02-系统实现/02.03-数据库缓存/02.03.06-云数据库缓存架构.md"], ["Heat Map"]),
    ("D12", "AI_Skill/skills/distributed-cache-algorithms/SKILL.md", ["1997"],
     ["docs/01-理论基础/01.03-分布式缓存算法/01.03.01-一致性哈希原理.md"], ["1997"]),
    ("D13", "AI_Skill/skills/cpu-cache-architecture/SKILL.md", ["64"],
     ["docs/02-系统实现/02.02-CPU缓存架构/02.02.03-Cache-Line对齐优化.md"], ["64"]),
    ("D14", "AI_Skill/skills/llm-kv-cache/SKILL.md", ["RadixAttention"],
     ["docs/04-架构设计/04.03-行业应用场景/04.03.15-大模型推理缓存架构.md"], ["RadixAttention"]),
    ("D15", "AI_Skill/skills/redis-data-structures/SKILL.md", ["Stream"],
     ["docs/04-架构设计/04.03-行业应用场景/04.03.19-Redis-Streams与消息队列边界.md"], ["XAUTOCLAIM"]),
]


def read(p):
    try:
        return (ROOT / p).read_text(encoding="utf-8")
    except OSError:
        return ""


def check_fingerprints():
    """判定指纹双端校验（全局一致性规范 §3）：决策图网 §0.3 的结论必须在权威源文档中出现"""
    FP = [
        ("F1", "无持久化", "docs/03-Redis组件/03.02-持久化机制/03.02.06-持久化策略全局决策与成本模型.md"),
        ("F2", "allkeys-lfu", "docs/03-Redis组件/03.04-内存管理/03.04.05-驱逐策略决策与近似误差.md"),
        ("F3", "everysec", "docs/03-Redis组件/03.02-持久化机制/03.02.06-持久化策略全局决策与成本模型.md"),
        ("F6", "版本号", "docs/04-架构设计/04.04-缓存问题与治理/04.04.08-缓存失效传播与一致性链路.md"),
        ("F8", "限流兜底", "docs/07-运维与部署/07.09-弹性伸缩与自愈/07.09.04-分片级弹性伸缩与分区迁移.md"),
        ("F11", "Kafka", "docs/04-架构设计/04.03-行业应用场景/04.03.19-Redis-Streams与消息队列边界.md"),
        ("F13", "直连", "docs/04-架构设计/04.06-架构工具/04.06.05-缓存代理层架构对比.md"),
        ("F17", "人工审批", "docs/07-运维与部署/07.09-弹性伸缩与自愈/07.09.04-分片级弹性伸缩与分区迁移.md"),
        ("F19", "unlogged", "docs/02-系统实现/02.03-数据库缓存/02.03.07-PostgreSQL18缓存能力与外部缓存边界.md"),
        ("F20", "版本化 URL", "docs/04-架构设计/04.03-行业应用场景/04.03.20-CDN与边缘缓存架构.md"),
        ("F22", "Valkey", "docs/03-Redis组件/03.05-Redis生态与版本演进/03.05.01-开源缓存技术全景图.md"),
    ]
    drifts = []
    for fid, needle, doc in FP:
        if needle not in read(doc):
            drifts.append(f"{fid}: 权威源缺判定结论 '{needle}' ({doc})")
    return drifts


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

    # 结构检查：技能分流目标必须真实存在（防止 → 不存在的技能）
    import re
    skills_dir = ROOT / "AI_Skill" / "skills"
    existing = {p.name for p in skills_dir.iterdir() if p.is_dir()}
    ref_pat = re.compile(
        r'→\s*(cache-[a-z-]+|redis-[a-z-]+|os-[a-z-]+|llm-[a-z-]+|cloud-[a-z-]+'
        r'|elastic-[a-z-]+|learning-[a-z-]+|cpu-[a-z-]+|db-[a-z-]+'
        r'|modern-[a-z-]+|distributed-[a-z-]+)')
    for sk in sorted(skills_dir.rglob("SKILL.md")):
        for m in ref_pat.finditer(sk.read_text(encoding="utf-8")):
            name = m.group(1)
            if name not in existing:
                results.append((f"ref:{sk.parent.name}->{name}", "DRIFT", [name], []))

    # 结构检查 2：判定指纹双端校验（决策图网结论 ↔ 权威源文档）
    for d in check_fingerprints():
        results.append((d.split(":")[0], "DRIFT", [d], []))

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
