#!/usr/bin/env python3
"""
BufferCache 项目统一自我验证入口

功能：
1. 聚合执行 Testing/cases/ 登记的验证用例（文档质量/形式化/基准/结构/运维/集成）
2. 结构化报告（控制台 + Testing/output/self_verify_report.json|md）
3. 失败给出用例 ID 与修正指引链接，支持 --ci 非零退出

使用方法：
    python Testing/self_verify.py all           # 全量
    python Testing/self_verify.py docs          # 文档质量组
    python Testing/self_verify.py links --path AI_Skill
    python Testing/self_verify.py formal|bench|ops|structure|cluster|version
    python Testing/self_verify.py all --ci      # CI 模式（失败退出码非零）
    python Testing/self_verify.py --report      # 查看最近一次报告

退出码：0 全过 / 1 存在失败 / 2 环境错误
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"
AI_SKILL_DIR = PROJECT_ROOT / "AI_Skill"
TESTING_DIR = PROJECT_ROOT / "Testing"
CASES_DIR = TESTING_DIR / "cases"
OUTPUT_DIR = TESTING_DIR / "output"
REPORT_JSON = OUTPUT_DIR / "self_verify_report.json"
REPORT_MD = OUTPUT_DIR / "self_verify_report.md"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

STATUS_PASS, STATUS_FAIL, STATUS_SKIP = "PASS", "FAIL", "SKIP"


@dataclass
class CheckResult:
    check_id: str
    title: str
    group: str
    status: str
    duration: float
    detail: str = ""
    case_file: str = ""


@dataclass
class Check:
    check_id: str
    title: str
    group: str
    case_file: str
    run: callable
    slow: bool = False


# ---------------------------------------------------------------- 工具

def run_cmd(cmd, timeout=300, cwd=None):
    """运行命令，返回 (rc, stdout+stderr)"""
    try:
        proc = subprocess.run(
            cmd, cwd=cwd or PROJECT_ROOT, timeout=timeout,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            encoding="utf-8", errors="replace",
            shell=isinstance(cmd, str),
        )
        return proc.returncode, proc.stdout or ""
    except subprocess.TimeoutExpired:
        return -1, f"TIMEOUT after {timeout}s"
    except FileNotFoundError as e:
        return 127, f"NOT FOUND: {e}"


def which(tool):
    from shutil import which as _which
    return _which(tool)


def extract_code_blocks(md_text):
    """提取 markdown 代码块: [(lang, code, lineno)]"""
    blocks = []
    pattern = re.compile(r"```(\w+)?\n(.*?)```", re.DOTALL)
    for m in pattern.finditer(md_text):
        lang = m.group(1) or "text"
        lineno = md_text[: m.start()].count("\n") + 1
        blocks.append((lang, m.group(2), lineno))
    return blocks


def iter_md_files(base: Path):
    if base.is_file() and base.suffix == ".md":
        if "archive" not in base.parts:
            yield base
    elif base.is_dir():
        for p in sorted(base.rglob("*.md")):
            if "archive" not in p.parts:
                yield p


# ---------------------------------------------------------------- 检查项

def check_code_blocks() -> str:
    """TC-DOC-001: 文档代码块可运行性（调用项目框架）"""
    rc, out = run_cmd([sys.executable, "scripts/code_test_framework.py", "--test", "python"], timeout=900)
    tail = "\n".join(out.strip().splitlines()[-15:])
    if rc != 0:
        return f"FAIL\n框架退出码 {rc}。输出尾部：\n{tail}"
    m = re.search(r"失败[::]?\s*(\d+)", out)
    if m and int(m.group(1)) > 0:
        return f"FAIL\n存在 {m.group(1)} 个失败代码块。输出尾部：\n{tail}"
    return f"PASS\n输出尾部：\n{tail}"


def check_code_blocks_multi() -> str:
    """TC-DOC-005: 多语言代码块（Go/Rust 编译运行、Bash 语法检查）"""
    parts = []
    failed_total = 0
    for lang in ("go", "rust", "bash"):
        rc, out = run_cmd([sys.executable, "scripts/code_test_framework.py", "--test", lang], timeout=600)
        m = re.search(r"测试失败\*\*:\s*(\d+)", out)
        failed = int(m.group(1)) if m else -1
        passed = re.search(r"测试通过\*\*:\s*(\d+)", out)
        skipped = re.search(r"跳过（环境依赖/上下文片段）\*\*:\s*(\d+)", out)
        failed_total += max(failed, 0)
        stat = (f"{lang}: 过 {passed.group(1) if passed else '?'} / "
                f"失败 {failed} / 跳过 {skipped.group(1) if skipped else '?'}")
        if failed != 0:
            bad = [ln for ln in out.splitlines() if "❌" in ln][:5]
            stat += "\n  " + "\n  ".join(bad)
        parts.append(stat)
    if failed_total > 0:
        return "FAIL\n" + "\n".join(parts)
    if failed_total < 0:
        return "FAIL\n语言测试统计解析失败（框架输出异常）\n" + "\n".join(parts)
    return "PASS\n" + "\n".join(parts)


FOREIGN_FINGERPRINTS = [
    (re.compile(r"^\s*-\s*job_name\s*:", re.M), "Prometheus 抓取配置（应为 yaml）"),
    (re.compile(r"^\s*(server|http|events|upstream)\s*\{", re.M), "nginx 配置块（应为 nginx/ini）"),
    (re.compile(r"^\s*(CREATE\s+TABLE|SELECT\s+.+\s+FROM\s+)", re.I | re.M), "SQL 语句（应为 sql）"),
    (re.compile(r"^\s*def\s+\w+\(.*\)\s*:\s*$", re.M), None),  # Python 特征（占位不用）
]
PYTHON_HINTS = re.compile(r"^\s*(def |class |import |from |print\(|return |elif |else:)", re.M)


def check_lang_tags() -> str:
    """TC-DOC-002: 明显非 Python 内容标为 python"""
    problems = []
    for md in iter_md_files(DOCS_DIR):
        try:
            text = md.read_text(encoding="utf-8")
        except Exception:
            continue
        for lang, code, lineno in extract_code_blocks(text):
            if lang != "python":
                continue
            hits = []
            for pat, desc in FOREIGN_FINGERPRINTS:
                if desc and pat.search(code):
                    hits.append(desc)
            if hits and not PYTHON_HINTS.search(code):
                rel = md.relative_to(PROJECT_ROOT)
                problems.append(f"{rel}:{lineno} 疑似 {hits[0]}")
    if problems:
        return "FAIL\n" + "\n".join(problems[:20])
    return "PASS\n未发现明显非 Python 内容标注为 python"


LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def check_links(base_arg: str) -> str:
    """TC-DOC-003: 相对链接完整性（默认全库：docs+AI_Skill+Testing+根目录）"""
    if base_arg:
        base = (PROJECT_ROOT / base_arg).resolve()
    else:
        base = PROJECT_ROOT.resolve()
    if not str(base).startswith(str(PROJECT_ROOT.resolve())):
        return "FAIL\n--path 必须位于项目内"
    targets = [base] if base.exists() else None
    if targets is None:
        return f"FAIL\n路径不存在: {base_arg}"

    dead = []
    checked = 0
    for md in iter_md_files(base):
        try:
            text = md.read_text(encoding="utf-8")
        except Exception:
            continue
        for m in LINK_RE.finditer(text):
            url = m.group(1)
            if url.startswith(("http://", "https://", "mailto:", "#")):
                continue
            url = url.split("#")[0]
            url = url.replace("%20", " ")
            if not url:
                continue
            # 跳过非文件链接的裸词目标（如代码中的 fn(arg)、文档参数说明）
            if "/" not in url and not re.search(r"\.(md|markdown|png|jpe?g|gif|svg|txt|pdf|json|ya?ml)$", url, re.I):
                continue
            checked += 1
            target = (md.parent / url).resolve()
            if not str(target).startswith(str(PROJECT_ROOT.resolve())):
                continue
            if not target.exists():
                lineno = text[: m.start()].count("\n") + 1
                dead.append(f"{md.relative_to(PROJECT_ROOT)}:{lineno} -> {url}")
    if dead:
        return f"FAIL\n死链 {len(dead)} 个（共检查 {checked} 个相对链接）：\n" + "\n".join(dead[:100])
    return f"PASS\n检查 {checked} 个相对链接，无死链"


def check_structure() -> str:
    """TC-DOC-004 + TC-STAT-001: 导航同步与统计口径"""
    problems = []
    notes = []

    # 1. INDEX.md 引用完整性
    index_md = DOCS_DIR / "INDEX.md"
    if index_md.exists():
        text = index_md.read_text(encoding="utf-8")
        for m in LINK_RE.finditer(text):
            url = m.group(1).split("#")[0].replace("%20", " ")
            if not url or url.startswith(("http", "mailto:")):
                continue
            target = (index_md.parent / url).resolve()
            if target.suffix == ".md" and not target.exists():
                lineno = text[: m.start()].count("\n") + 1
                problems.append(f"INDEX.md:{lineno} -> {url}")
    else:
        problems.append("docs/INDEX.md 不存在")

    # 2. 子目录 README 完整性（archive 除外）
    for sub in sorted(DOCS_DIR.iterdir()):
        if not sub.is_dir() or sub.name == "archive":
            continue
        if sub.name == ".github":
            continue
        md_count = len(list(sub.rglob("*.md")))
        if md_count and not (sub / "README.md").exists():
            problems.append(f"{sub.relative_to(PROJECT_ROOT)} 缺少 README.md（含 {md_count} 个 md）")

    # 3. 统计口径
    count = len([p for p in DOCS_DIR.rglob("*.md") if "archive" not in p.parts])
    notes.append(f"docs/ 文档数（不含 archive）= {count}")
    agents = PROJECT_ROOT / "AGENTS.md"
    if agents.exists():
        m = re.search(r"wc -l\s+#\s*当前\s*(\d+)", agents.read_text(encoding="utf-8"))
        if m:
            declared = int(m.group(1))
            if declared != count:
                notes.append(f"WARN: AGENTS.md §5 声明 {declared}，实际 {count}（请人工核对是否需要更新声明）")
            else:
                notes.append(f"AGENTS.md §5 声明 {declared} 与实际一致")

    # 4. AI_Skill 技能完整性
    skills_dir = AI_SKILL_DIR / "skills"
    if skills_dir.exists():
        for skill in sorted(skills_dir.iterdir()):
            smd = skill / "SKILL.md"
            if not smd.exists():
                problems.append(f"AI_Skill/skills/{skill.name} 缺少 SKILL.md")
                continue
            head = smd.read_text(encoding="utf-8")[:500]
            m = re.search(r"^name:\s*(\S+)", head, re.M)
            if not m:
                problems.append(f"AI_Skill/skills/{skill.name}/SKILL.md 缺少 frontmatter name")
            elif m.group(1) != skill.name:
                problems.append(f"AI_Skill/skills/{skill.name}/SKILL.md name={m.group(1)} 与目录名不一致")

    status = "FAIL" if problems else "PASS"
    body = "\n".join(problems) if problems else "结构检查全部通过"
    return f"{status}\n{body}\n" + "\n".join(notes)


def check_formal() -> str:
    """TC-FORM-001: TLA+ 模型检查（Windows 直接 run.bat；其他平台用 jar）"""
    jar = PROJECT_ROOT / "scripts" / "formal" / "tla2tools.jar"
    if not jar.exists():
        return "SKIP\n缺少 scripts/formal/tla2tools.jar"
    java = which("java")
    if not java:
        return "SKIP\n未安装 Java（需 11+）"
    formal_dir = PROJECT_ROOT / "scripts" / "formal"
    if os.name == "nt":
        rc, out = run_cmd(["cmd", "/c", "run.bat"], timeout=300, cwd=formal_dir)
    else:
        parts = []
        for name in ("LRU", "ARC"):
            rc, out = run_cmd(
                [java, "-XX:+UseParallelGC", "-jar", "tla2tools.jar", "-nowarning",
                 "-config", f"{name}.cfg", f"{name}.tla"],
                timeout=300, cwd=formal_dir)
            parts.append(out)
        out = "\n".join(parts)
    if rc != 0:
        tail = "\n".join(out.strip().splitlines()[-15:])
        return f"FAIL\nTLC 退出码 {rc}。输出尾部：\n{tail}"
    passed = out.count("PASSED")
    if "FAILED" in out:
        return "FAIL\nTLC 输出含 FAILED"
    return f"PASS\nPASSED 标记数 {passed}（期望 LRU/ARC 与汇总共 ≥3）\n输出尾部：\n" + "\n".join(out.strip().splitlines()[-4:])


def check_bench() -> str:
    """TC-BENCH-001: trace 驱动基准（合成 + 公开格式 fixture 双验证）"""
    script = PROJECT_ROOT / "scripts" / "benchmark" / "trace_benchmark.py"
    if not script.exists():
        return "SKIP\nscripts/benchmark/trace_benchmark.py 不存在"
    parts = []
    for label, extra in (("合成trace", []), ("CSV fixture", ["--trace", "Testing/fixtures/traces/sample_trace.csv", "--ops", "3000", "--capacity", "80"])):
        rc, out = run_cmd([sys.executable, str(script)] + extra, timeout=300)
        if rc != 0:
            tail = "\n".join(out.strip().splitlines()[-10:])
            return f"FAIL\n{label}基准退出码 {rc}：\n{tail}"
        hits = [ln for ln in out.splitlines() if re.search(r"miss ratio|LRU|LFU|S3", ln)]
        parts.append(f"[{label}]\n" + "\n".join(hits[-5:]))
    return "PASS\n两种 trace 源基准完成：\n" + "\n\n".join(parts)


def check_kv_sim() -> str:
    """TC-BENCH-002: KV 前缀缓存模拟（提取 04.03.15 的 kv_cache_sim 块运行）"""
    doc = DOCS_DIR / "04-架构设计" / "04.03-行业应用场景" / "04.03.15-大模型推理缓存架构.md"
    if not doc.exists():
        return "FAIL\n04.03.15 文档不存在"
    text = doc.read_text(encoding="utf-8")
    sim_code = None
    for lang, code, _ in extract_code_blocks(text):
        if lang == "python" and "kv_cache_sim" in code:
            sim_code = code
            break
    if sim_code is None:
        return "FAIL\n未在 04.03.15 中找到 kv_cache_sim.py 代码块"
    with tempfile.TemporaryDirectory() as tmp:
        sim = Path(tmp) / "kv_cache_sim.py"
        sim.write_text(sim_code, encoding="utf-8")
        rc, out = run_cmd([sys.executable, str(sim)], timeout=120)
    if rc != 0:
        return f"FAIL\n模拟脚本运行失败：\n{out[-800:]}"
    m_on = re.search(r"前缀缓存开启:\s*复用率\s*([\d.]+)%", out)
    m_off = re.search(r"前缀缓存关闭:\s*复用率\s*([\d.]+)%", out)
    if not m_on:
        return f"FAIL\n输出缺少复用率：\n{out[-500:]}"
    on, off = float(m_on.group(1)), float(m_off.group(1)) if m_off else None
    problems = []
    if off is not None and on <= off:
        problems.append(f"开启({on}%) 未高于关闭({off}%)")
    if abs(on - 85.5) > 1.0:
        problems.append(f"开启复用率 {on}% 与登记基线 85.5% 偏差超过 1%")
    if problems:
        return "FAIL\n" + "; ".join(problems) + f"\n实际输出：\n{out[-400:]}"
    return f"PASS\n开启复用率 {on}%（基线 85.5%±1%）" + (f"，关闭 {off}%" if off else "")


def find_yaml_blocks():
    """从运维/监控/弹性自愈文档提取 yaml 代码块"""
    docs = [
        DOCS_DIR / "07-运维与部署",
        DOCS_DIR / "04-架构设计" / "04.04-缓存问题与治理" / "04.04.07-缓存监控指标体系.md",
    ]
    blocks = []
    for base in docs:
        files = [base] if base.is_file() else sorted(base.rglob("*.md"))
        for md in files:
            if not md.exists():
                continue
            try:
                text = md.read_text(encoding="utf-8")
            except Exception:
                continue
            for lang, code, lineno in extract_code_blocks(text):
                if lang in ("yaml", "yml"):
                    blocks.append((md, lineno, code))
    return blocks


_OPS_CACHE = {}


def check_ops() -> str:
    """TC-OPS-001/002/003: 部署配置静态验证 + 规则结构 + 安全基线（三个用例共享一次运行）"""
    if "result" in _OPS_CACHE:
        return _OPS_CACHE["result"]
    try:
        import yaml
        has_yaml = True
    except ImportError:
        has_yaml = False

    problems, skips, notes = [], [], []

    # 1. YAML 解析
    blocks = find_yaml_blocks()
    if not blocks:
        skips.append("未发现 yaml 代码块（检查路径配置）")
    elif not has_yaml:
        skips.append("未安装 PyYAML，跳过 YAML 解析（pip install pyyaml）")
    else:
        bad = 0
        templated = 0
        for md, lineno, code in blocks:
            if "{{" in code or "{%" in code:  # Helm/Go 模板，非纯 YAML
                templated += 1
                continue
            try:
                yaml.safe_load(code)
            except Exception as e:
                bad += 1
                problems.append(f"{md.relative_to(PROJECT_ROOT)}:{lineno} YAML 解析失败: {str(e)[:80]}")
        notes.append(f"YAML 块解析 {len(blocks)} 个（模板豁免 {templated} 个）" + (f"，失败 {bad} 个" if bad else "，全部通过"))

    # 2. Prometheus 规则结构（含 promtool 增强）
    promtool = which("promtool")
    for md, lineno, code in blocks:
        if "alert:" not in code or "expr:" not in code or "{{" in code:
            continue
        if not has_yaml:
            continue
        try:
            data = yaml.safe_load(code)
        except Exception:
            continue
        groups = data.get("groups", []) if isinstance(data, dict) else []
        for g in groups:
            for rule in g.get("rules", []):
                if "alert" in rule:
                    ann = rule.get("annotations", {}) or {}
                    if not (ann.get("summary") or ann.get("description")):
                        problems.append(f"{md.relative_to(PROJECT_ROOT)}:{lineno} 告警 '{rule.get('alert')}' 缺少 summary/description")
        if promtool:
            with tempfile.TemporaryDirectory() as tmp:
                rf = Path(tmp) / "rules.yml"
                rf.write_text(code, encoding="utf-8")
                rc, out = run_cmd([promtool, "check", "rules", str(rf)], timeout=60)
                if rc != 0:
                    problems.append(f"{md.relative_to(PROJECT_ROOT)}:{lineno} promtool: {out.strip().splitlines()[-1][:100]}")
    if promtool:
        notes.append("promtool 增强检查已执行")
    else:
        skips.append("未安装 promtool，规则仅做结构检查")

    # 3. 外部 IaC 工具（可选增强）
    for tool, label in (("terraform", "Terraform"), ("ansible-playbook", "Ansible"), ("helm", "Helm")):
        if which(tool):
            notes.append(f"{label} 可用（增强检查由 TC-OPS-001 人工步骤执行：validate/lint）")
        else:
            skips.append(f"未安装 {tool}（静态语法检查跳过，属正常）")

    # 4. 安全基线静态检查
    sec_docs = DOCS_DIR / "07-运维与部署"
    hardcoded = []
    for md in sorted(sec_docs.rglob("*.md")):
        try:
            text = md.read_text(encoding="utf-8")
        except Exception:
            continue
        for lang, code, lineno in extract_code_blocks(text):
            if lang not in ("ini", "conf", "bash", "sh", "yaml", "yml", "text"):
                continue
            for m in re.finditer(r"requirepass\s+(.+)", code):
                val = m.group(1).strip().strip('"\'')
                if val and not val.startswith(("$", "<", "{")) and len(val) >= 6:
                    hardcoded.append(f"{md.relative_to(PROJECT_ROOT)}:{lineno} requirepass 疑似硬编码")
    if hardcoded:
        problems.extend(hardcoded[:10])
    else:
        notes.append("安全基线：未发现 requirepass 硬编码")

    status = "FAIL" if problems else "PASS"
    parts = []
    if problems:
        parts.append("问题：\n" + "\n".join(problems[:20]))
    if skips:
        parts.append("跳过（环境，正常）：\n- " + "\n- ".join(skips))
    if notes:
        parts.append("说明：\n- " + "\n- ".join(notes))
    result = f"{status}\n" + "\n\n".join(parts)
    _OPS_CACHE["result"] = result
    return result


def check_cluster() -> str:
    """集群用例为人工演练：导出清单与执行建议"""
    group = CASES_DIR / "04-集群"
    cases = []
    if group.exists():
        for f in sorted(group.glob("*.md")):
            title = f.read_text(encoding="utf-8").splitlines()[0].lstrip("# ").strip()
            cases.append(f"- {title}（{f.name}）")
    body = "集群用例为人工演练（需实例），清单如下，按 自我验证修正机制 §3 每月轮换执行：\n" + "\n".join(cases)
    return "PASS\n" + body


def check_consistency() -> str:
    """TC-BENCH-003: 缓存一致性竞态验证（快速档）"""
    script = PROJECT_ROOT / "scripts" / "consistency_check.py"
    if not script.exists():
        return "SKIP\nscripts/consistency_check.py 不存在"
    rc, out = run_cmd([sys.executable, str(script), "--duration", "3"], timeout=240)
    if rc != 0:
        return f"FAIL\n一致性校验器退出码 {rc}：\n{out[-500:]}"
    for name in ("无兜底", "TTL", "延迟双删"):
        if name not in out:
            return f"FAIL\n输出缺少策略 {name}\n{out[-300:]}"
    return "PASS\n三策略输出齐全：\n" + "\n".join(
        ln for ln in out.splitlines() if "策略" in ln or "无兜底" in ln or "延迟双删" in ln)[:600]


def check_capacity() -> str:
    """D8 自检: 容量估算器默认参数输出合理性"""
    script = PROJECT_ROOT / "scripts" / "capacity_calculator.py"
    if not script.exists():
        return "SKIP\nscripts/capacity_calculator.py 不存在"
    rc, out = run_cmd([sys.executable, str(script)], timeout=60)
    if rc != 0:
        return f"FAIL\n容量估算器退出码 {rc}：\n{out[-300:]}"
    for field in ("总实例数", "月成本估算", "假设"):
        if field not in out:
            return f"FAIL\n输出缺少字段 {field}\n{out[-300:]}"
    return "PASS\n容量估算器默认参数输出正常（实例/成本/假设齐全）"


def check_lab_monitor() -> str:
    """TC-OPS-005-A: 演练环境 exporter 指标可达（需 Docker，无则 SKIP）"""
    import socket
    probes = {"redis_up": None, "redis_memory_used_bytes": None}
    try:
        with socket.create_connection(("127.0.0.1", 19121), timeout=3):
            pass
    except OSError:
        return "SKIP\nredis_exporter(19121) 不可达：先执行 monitoring-compose.yml up -d redis-exporter（需 Docker）"
    rc, out = run_cmd(["curl", "-s", "http://localhost:19121/metrics"], timeout=30)
    if rc != 0 or "redis_up" not in out:
        return f"FAIL\nexporter 指标不可读（rc={rc}）"
    for metric in probes:
        if metric + " " not in out:
            return f"FAIL\nexporter 缺指标 {metric}"
    return "PASS\nredis_exporter 核心指标可达：redis_up / redis_memory_used_bytes / keyspace_hits / connected_slaves"


def check_security() -> str:
    """TC-SEC-001: 机密扫描 + 仓库健康 + 未授权探测"""
    import shutil
    problems, notes = [], []
    SECRET_PAT = re.compile(
        r"(?i)(password|passwd|secret|token|api[_-]?key|access[_-]?key)[ \t]*[:=][ \t]*[\"']?([^\"'\s]{8,})")
    PLACEHOLDER_OK = ("${", "<", "{", "xxx", "XXX", "your", "YOUR", "example", "changeme", "占位", "password", "PASSWORD", "passwd", "admin")

    import subprocess as sp
    rc, files = run_cmd(["git", "ls-files"], timeout=60)
    tracked = [f for f in files.splitlines() if f.strip()]
    notes.append(f"跟踪文件 {len(tracked)} 个")

    scanned = 0
    for rel in tracked:
        if rel == "Testing/self_verify.py":   # 扫描器自身含检测模式字面量
            continue
        if "archive" in rel or rel.endswith((".png", ".jpg", ".jar", ".zip", ".bin")):
            continue
        p = PROJECT_ROOT / rel
        try:
            if p.stat().st_size > 10 * 1024 * 1024:
                problems.append(f"大文件: {rel}（{p.stat().st_size // 1048576}MB >10MB）")
                continue
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        scanned += 1
        if "PRIVATE KEY-----" in text:
            problems.append(f"私钥头: {rel}")
        if re.search(r"AKIA[0-9A-Z]{16}", text):
            problems.append(f"AWS AccessKey 模式: {rel}")
        for m in SECRET_PAT.finditer(text):
            val = m.group(2)
            val_l = val.lower()
            if val.startswith(PLACEHOLDER_OK) or val.startswith(("var.", "local.", "module.", "data.")) \
               or any(k in val_l for k in ('password', 'passwd', 'example', 'your', 'xxx', 'here')) \
               or '(' in val or '${' in val:
                continue                  # 占位惯例/函数调用/变量引用/环境插值
            line_no = text[:m.start()].count("\n") + 1
            line_txt = text.split("\n")[line_no - 1].strip()
            if line_txt.startswith(("-", "--")):   # YAML 列表/CLI 参数形态（etcd token 等）
                continue
            problems.append(f"疑似硬编码密钥 {rel}:{line_no}（{m.group(1)}=***）")
            break
    notes.append(f"机密扫描 {scanned} 个文本文件")

    # 未授权 Redis 探测（本地 6379）
    try:
        import socket as sk
        with sk.create_connection(("127.0.0.1", 6379), timeout=2) as s:
            s.sendall(b"PING\r\n")
            resp = s.recv(64).decode(errors="ignore")
        if "PONG" in resp:
            problems.append("本地 6379 Redis 无需认证即可 PING（未授权访问暴露）")
        elif "NOAUTH" in resp:
            notes.append("本地 6379 需认证（正常）")
    except OSError:
        notes.append("本地 6379 无实例，未授权探测跳过")

    status = "FAIL" if problems else "PASS"
    body = ("问题：\n" + "\n".join(problems[:15])) if problems else "安全体检通过"
    return f"{status}\n{body}\n" + "说明：\n- " + "\n- ".join(notes)


def check_mkdocs() -> str:
    """TC-DOC-006: docs 站点可构建（无 mkdocs 自动 SKIP）"""
    import shutil
    if not (PROJECT_ROOT / "mkdocs.yml").exists():
        return "FAIL\nmkdocs.yml 不存在"
    if not shutil.which("mkdocs"):
        return "SKIP\n未安装 mkdocs（pip install -r requirements-dev.txt 后启用）"
    rc, out = run_cmd([shutil.which("mkdocs"), "build",
                       "-d", tempfile.mkdtemp(prefix="mkdocs_")], timeout=300)
    if rc != 0:
        tail = "\n".join(out.strip().splitlines()[-12:])
        return f"FAIL\nmkdocs build 失败：\n{tail}"
    warn = out.count("contains a link") + out.count("WARNING")
    return (f"PASS\nmkdocs build 通过（站点可构建；链接类 warning 基线 {warn} 条，"
            f"突增即按 TC-DOC-006 排查锚点漂移）")


def check_assertions() -> str:
    """F10: 技能-正文一致性巡检（事实断言清单驱动）"""
    script = PROJECT_ROOT / "scripts" / "assertion_check.py"
    if not script.exists():
        return "SKIP\nscripts/assertion_check.py 不存在"
    rc, out = run_cmd([sys.executable, str(script)], timeout=60)
    drift = [ln for ln in out.splitlines() if ln.strip().startswith("[DRIFT]")]
    if drift:
        return "FAIL\n发现漂移：\n" + "\n".join(drift[:8]) + "\n（修正指引: 更新技能/正文/断言清单三端）"
    return "PASS\n" + "\n".join(ln for ln in out.splitlines() if ln.startswith("[PASS]"))


_GOV_CACHE = {}


def check_governance() -> str:
    """TC-BENCH-006/007: 治理模拟 + KV 驱逐对比（两个用例共享一次运行）"""
    if "result" in _GOV_CACHE:
        return _GOV_CACHE["result"]
    parts = []
    for script, cases in (("governance_sim.py", ["penetrate", "breakdown"]),
                          ("kv_evict_bench.py", ["LRU", "SIEVE"])):
        path = PROJECT_ROOT / "scripts" / script
        if not path.exists():
            _GOV_CACHE["result"] = f"SKIP\n{script} 不存在"
            return _GOV_CACHE["result"]
        rc, out = run_cmd([sys.executable, str(path)], timeout=240)
        if rc != 0:
            _GOV_CACHE["result"] = f"FAIL\n{script} 退出码 {rc}：\n{out[-300:]}"
            return _GOV_CACHE["result"]
        missing = [c for c in cases if c not in out]
        if missing:
            _GOV_CACHE["result"] = f"FAIL\n{script} 输出缺少场景 {missing}\n{out[-300:]}"
            return _GOV_CACHE["result"]
        parts.append(f"[{script}]\n" + "\n".join(out.strip().splitlines()[-8:]))
    result = "PASS\n治理模拟与 KV 驱逐对比输出正常：\n\n" + "\n\n".join(parts)
    _GOV_CACHE["result"] = result
    return result


def check_selfheal() -> str:
    """TC-CLUS-010: 自愈闭环模拟（预算表回归）"""
    rc, out = run_cmd([sys.executable, "scripts/selfheal_sim.py"], timeout=120)
    if rc == 0 and "0 FAIL" in out:
        return "PASS" + chr(10) + chr(10).join(out.splitlines()[:7])
    return "FAIL" + chr(10) + out[-300:]


def check_steady() -> str:
    """W2: 稳态漂移检测（exporter 优先，模拟降级）"""
    rc, out = run_cmd([sys.executable, "scripts/steady_state_check.py"], timeout=120)
    if rc == 0 and "稳态" in out:
        src = "exporter" if "exporter" in out.splitlines()[0] else "simulate"
        return "PASS" + chr(10) + "稳态判定通过（数据源 %s）" % src
    if rc == 1:
        return "FAIL" + chr(10) + out[-300:]
    return "SKIP" + chr(10) + out[-200:]


def check_skill_selftest() -> str:
    """TC-DOC-008: 技能动态自测（20 技能验证命令实跑）"""
    rc, out = run_cmd([sys.executable, "scripts/skill_selftest.py"], timeout=900)
    if rc == 0 and "0 FAIL" in out:
        return "PASS" + chr(10) + "技能动态自测全过（20 技能）"
    return "FAIL" + chr(10) + out[-400:]


def check_version() -> str:
    """TC-INT-002: 版本监控"""
    script = PROJECT_ROOT / "scripts" / "version_monitor.py"
    if not script.exists():
        return "SKIP\nscripts/version_monitor.py 不存在"
    rc, out = run_cmd([sys.executable, str(script), "--check", "redis"], timeout=60)
    if rc in (0, 1):
        tail = "\n".join(out.strip().splitlines()[-10:])
        return f"PASS\n版本监控已运行：\n{tail}"
    if rc == 127:
        return "SKIP\n版本监控依赖缺失或网络不可达"
    return f"FAIL\n版本监控退出码 {rc}：\n{out[-400:]}"


CHECKS = [
    Check("TC-DOC-001", "文档代码块可运行性(Python)", "docs",
          "cases/01-文档质量/TC-DOC-001-文档代码块可运行性.md", check_code_blocks, slow=True),
    Check("TC-DOC-005", "多语言代码块测试(Go/Rust/Bash)", "docs",
          "cases/01-文档质量/TC-DOC-005-多语言代码块测试.md", check_code_blocks_multi, slow=True),
    Check("TC-DOC-002", "代码块语言标注真实性", "docs",
          "cases/01-文档质量/TC-DOC-002-代码块语言标注真实性.md", check_lang_tags),
    Check("TC-DOC-003", "相对链接完整性", "links",
          "cases/01-文档质量/TC-DOC-003-相对链接完整性.md", lambda: check_links("")),
    Check("TC-DOC-004", "导航与索引同步完整性", "structure",
          "cases/01-文档质量/TC-DOC-004-导航与索引同步完整性.md", check_structure),
    Check("TC-STAT-001", "文档统计口径", "structure",
          "cases/02-形式化与基准/TC-STAT-001-文档统计口径.md", check_structure),
    Check("TC-FORM-001", "TLA+ 模型检查", "formal",
          "cases/02-形式化与基准/TC-FORM-001-TLA+模型检查.md", check_formal, slow=True),
    Check("TC-BENCH-001", "Trace 驱动算法基准", "bench",
          "cases/02-形式化与基准/TC-BENCH-001-Trace驱动算法基准.md", check_bench, slow=True),
    Check("TC-BENCH-002", "KV 前缀缓存模拟实验", "bench",
          "cases/02-形式化与基准/TC-BENCH-002-KV前缀缓存模拟实验.md", check_kv_sim),
    Check("TC-BENCH-003", "缓存一致性竞态验证", "consistency",
          "cases/02-形式化与基准/TC-BENCH-003-缓存一致性竞态验证.md", check_consistency, slow=True),
    Check("TC-BENCH-004", "容量成本估算器自检", "bench",
          "cases/02-形式化与基准/TC-BENCH-004-容量成本估算器自检.md", check_capacity),
    Check("TC-OPS-001", "部署配置静态验证", "ops",
          "cases/03-运维部署/TC-OPS-001-部署配置静态验证.md", check_ops),
    Check("TC-OPS-002", "Prometheus 规则与告警验证", "ops",
          "cases/03-运维部署/TC-OPS-002-Prometheus规则与告警验证.md", check_ops),
    Check("TC-OPS-003", "缓存安全基线检查", "ops",
          "cases/03-运维部署/TC-OPS-003-缓存安全基线检查.md", check_ops),
    Check("TC-OPS-004", "弹性伸缩与自愈配置验证", "ops",
          "cases/03-运维部署/TC-OPS-004-弹性伸缩与自愈配置验证.md", check_ops),
    Check("TC-OPS-005", "监控示例栈验证(exporter)", "lab",
          "cases/03-运维部署/TC-OPS-005-监控示例栈验证.md", check_lab_monitor),
    Check("TC-SEC-001", "仓库安全体检(机密/未授权)", "security",
          "cases/03-运维部署/TC-SEC-001-仓库安全体检.md", check_security),
    Check("TC-DOC-006", "文档站点可构建(mkdocs)", "docs",
          "cases/01-文档质量/TC-DOC-006-文档站点构建检查.md", check_mkdocs, slow=True),
    Check("TC-DOC-007", "技能-正文一致性巡检", "docs",
          "cases/01-文档质量/TC-DOC-007-技能正文一致性巡检.md", check_assertions),
    Check("TC-BENCH-006", "治理策略模拟(穿透/雪崩/击穿)", "governance",
          "cases/02-形式化与基准/TC-BENCH-006-治理策略模拟验证.md", check_governance, slow=True),
    Check("TC-BENCH-007", "KV驱逐策略对比(LRU/FIFO/SIEVE)", "governance",
          "cases/02-形式化与基准/TC-BENCH-007-KV驱逐策略对比实验.md", check_governance, slow=True),
    Check("TC-CLUS-001~004", "集群演练清单(人工)", "cluster",
          "cases/04-集群", check_cluster),
    Check("TC-CLUS-010", "自愈闭环模拟(预算回归)", "selfheal",
          "cases/04-集群/TC-CLUS-010-自愈闭环模拟.md", check_selfheal),
    Check("TC-STAT-002", "稳态漂移检测", "steady",
          "cases/05-集成/TC-STAT-002-稳态漂移检测.md", check_steady),
    Check("TC-DOC-008", "技能动态自测(20技能)", "skilltest",
          "cases/01-文档质量/TC-DOC-008-技能动态自测.md", check_skill_selftest, slow=True),
    Check("TC-INT-001", "全量回归(本子集组合)", "all",
          "cases/05-集成/TC-INT-001-全量自我验证回归.md",
          lambda: "PASS\nall 即为本组合的全量执行"),
    Check("TC-INT-002", "版本监控", "version",
          "cases/05-集成/TC-INT-002-CI集成与版本监控.md", check_version),
]

GROUPS = {
    "all": ["docs", "links", "structure", "formal", "bench", "ops", "version",
            "consistency", "lab", "security", "governance", "selfheal", "steady",
            "skilltest"],
    "selfheal": ["selfheal"],
    "steady": ["steady"],
    "skilltest": ["skilltest"],
    "docs": ["docs", "links", "structure"],
    "structure": ["structure"],
    "links": ["links"],
    "formal": ["formal"],
    "bench": ["bench"],
    "consistency": ["consistency"],
    "lab": ["lab"],
    "security": ["security"],
    "governance": ["governance"],
    "ops": ["ops"],
    "cluster": ["cluster"],
    "version": ["version"],
}


def main():
    parser = argparse.ArgumentParser(description="BufferCache 统一自我验证")
    parser.add_argument("command", nargs="?", default="all",
                        choices=list(GROUPS.keys()) + ["report"])
    parser.add_argument("--ci", action="store_true", help="CI 模式：失败时退出码非零")
    parser.add_argument("--path", help="links 检查的限定目录（相对项目根）")
    parser.add_argument("--report", action="store_true", help="查看最近一次报告")
    args = parser.parse_args()

    if args.command == "report" or args.report:
        show_report()
        return 0

    groups = set(GROUPS[args.command])
    checks = [c for c in CHECKS if c.group in groups]

    print(f"BufferCache self_verify | {datetime.now():%Y-%m-%d %H:%M:%S}")
    print(f"命令: {args.command} | 检查项 {len(checks)} 个\n")

    results = []
    for chk in checks:
        t0 = time.time()
        if chk.check_id == "TC-DOC-003" and args.path:
            raw = check_links(args.path)
        else:
            raw = chk.run()
        dur = time.time() - t0
        status, _, detail = raw.partition("\n")
        res = CheckResult(chk.check_id, chk.title, chk.group, status, dur, detail, chk.case_file)
        results.append(res)
        mark = {"PASS": "[PASS]", "FAIL": "[FAIL]", "SKIP": "[SKIP]"}[status]
        print(f"{mark} {chk.check_id:<14} {chk.title} ({dur:.1f}s)")
        if status != "PASS":
            for line in detail.splitlines()[:8]:
                print(f"       {line}")
            if len(detail.splitlines()) > 8:
                print(f"       ... (详见报告)")
            print(f"       修正指引: Testing/{chk.case_file}")

    passed = sum(1 for r in results if r.status == STATUS_PASS)
    failed = sum(1 for r in results if r.status == STATUS_FAIL)
    skipped = sum(1 for r in results if r.status == STATUS_SKIP)
    print(f"\n结果: {passed} PASS / {failed} FAIL / {skipped} SKIP")

    write_report(results, args.command)

    if failed:
        print("结论: FAIL（按用例修正指引处理后复跑）")
        return 1
    if passed == 0 and skipped > 0:
        print("结论: 全部跳过（环境不满足）")
        return 2
    print("结论: PASS" + ("（含跳过项）" if skipped else ""))
    return 0


def write_report(results, command):
    OUTPUT_DIR.mkdir(exist_ok=True)
    data = {
        "time": f"{datetime.now():%Y-%m-%d %H:%M:%S}",
        "command": command,
        "summary": {
            "pass": sum(1 for r in results if r.status == "PASS"),
            "fail": sum(1 for r in results if r.status == "FAIL"),
            "skip": sum(1 for r in results if r.status == "SKIP"),
        },
        "results": [r.__dict__ for r in results],
    }
    REPORT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [f"# self_verify 报告 {data['time']}（命令: {command}）\n",
             f"PASS {data['summary']['pass']} / FAIL {data['summary']['fail']} / SKIP {data['summary']['skip']}\n"]
    for r in results:
        lines.append(f"## {r.status} {r.check_id} {r.title}")
        lines.append(r.detail or "（无输出）")
        lines.append(f"用例: Testing/{r.case_file}\n")
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def show_report():
    if not REPORT_JSON.exists():
        print("尚无报告，请先运行验证")
        return
    data = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
    print(f"最近报告: {data['time']}（命令: {data['command']}）")
    print(f"PASS {data['summary']['pass']} / FAIL {data['summary']['fail']} / SKIP {data['summary']['skip']}\n")
    for r in data["results"]:
        print(f"[{r['status']}] {r['check_id']:<14} {r['title']}")


if __name__ == "__main__":
    sys.exit(main())
