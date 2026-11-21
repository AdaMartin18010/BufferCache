#!/usr/bin/env python3
# 能力矩阵生成器与一致对账门（M1 建立，M2+ 补批实现 --gen 全格铺底 2026-11-21）
# 用法:
#   matrix_gen.py --check   一致对账（self_verify 矩阵组门禁）:
#                           ① 维度 TSV 结构合法 ② 注册表行维度取值合法 ③ 注册表 case 文件存在
#                           ④ ID 全局唯一（00-05 职能域 + 注册表；矩阵层自身文件不计入"既有"）
#                           ⑤ 适用矩阵含全部 7 矩阵
#   matrix_gen.py --stats   覆盖看板数据（各矩阵格数/待补数/●数/登记数）→ stdout JSON
#   matrix_gen.py --gen     全格铺底：适用矩阵中所有 ●格（无 → 关联且无既有文件）生成 GWT 用例文件
#                           + 注册表 gen 行追加（幂等：已有文件/行则跳过）
# RC: 0=PASS；1=FAIL；--gen 环境阻塞格的用例带 SKIP 语义前置（执行=hermes）
import json
import re
import sys
from pathlib import Path

MX = Path(__file__).resolve().parent.parent          # Testing/08-能力矩阵
ROOT = MX.parent.parent                               # 仓库根
DIMS = MX / "维度定义"
REG = MX / "matrix-registry.tsv"
APPLY = MX / "适用矩阵.md"
CASES = MX / "cases"

MATRICES = {
    "MXA": ("MX-A-algos.tsv", "MX-A-methods.tsv"),
    "MXB": ("MX-B-forms.tsv", "MX-B-failures.tsv"),
    "MXC": ("MX-C-ratios.tsv", "MX-C-sizes.tsv", "MX-C-tools.tsv"),
    "MXD": ("MX-D-langs.tsv", "MX-D-ops.tsv"),
    "MXE": ("MX-E-domains.tsv", "MX-E-methods.tsv"),
    "MXF": ("MX-F-mechs.tsv", "MX-F-methods.tsv"),
    "MXG": ("MX-G-domains.tsv", "MX-G-quality.tsv"),
}

METHOD_ACTION = {
    "TLA": "TLA+ 模型检查（安全/活性不变式）",
    "TRACE": "trace_benchmark 回放（合成 Zipf/扫描 + 公开 CSV 嗅探）",
    "SIM": "离散模拟实验（--seed 固定可复现）",
    "COQ": "Coq 编译 + 引理验证（coqc 0 error，axiom 清单显式）",
    "UNIT": "属性单测（固定种子随机序列断言不变式）",
    "STATIC": "静态规则检查（配置/规则文件结构合法）",
    "LIVE": "实载断言（容器内命令行为验证）",
    "DYN": "动态探测（端口/行为探测）",
}

FAILURE_ACTION = {
    "KILL": "节点宕机（stop/kill 容器）",
    "PART": "网络分区（toxiproxy/网络隔离）",
    "LAT": "网络延迟注入（toxiproxy latency toxic）",
    "DISK": "磁盘压力注入（数据卷写满模拟）",
    "CLK": "时钟漂移（容器内时间调整）",
    "SLOW": "慢查询阻塞（DEBUG SLEEP 循环）",
}


def load_dim(tsv):
    """返回 (codes, {code: (name, source)})"""
    codes, meta = [], {}
    for i, line in enumerate(tsv.read_text(encoding="utf-8").splitlines()):
        if not line.strip() or line.startswith("#"):
            continue
        p = line.split("\t")
        if i == 0:
            if p[:3] != ["code", "name", "source"]:
                raise ValueError(f"{tsv.name} 表头非法: {p[:3]}")
            continue
        if len(p) < 3:
            raise ValueError(f"{tsv.name} 行列数 <3: {line}")
        codes.append(p[0].strip())
        meta[p[0].strip()] = (p[1].strip(), p[2].strip())
    return codes, meta


def load_all_dims():
    dims = {}
    for mx, files in MATRICES.items():
        dims[mx] = []
        for fn in files:
            dims[mx].append(load_dim(DIMS / fn))
    return dims


def registry_rows():
    rows = []
    if not REG.exists():
        return rows
    for line in REG.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        p = line.split("\t")
        if p[0] == "case_id":
            continue
        rows.append(p)
    return rows


def existing_case_ids(include_matrix=False):
    ids = set()
    bases = [ROOT / "Testing" / "cases"]
    if include_matrix:
        bases.append(CASES)
    for base in bases:
        if not base.exists():
            continue
        for f in base.rglob("TC-*.md"):
            m = re.match(r"(TC-[A-Za-z0-9-]+?)(?:-\d+)?\.md$", f.name)
            if m:
                ids.add(m.group(1))
    return ids


def parse_cells():
    """解析适用矩阵 → [(mx, d1, d2, d3|None, cell_text)]"""
    dims = load_all_dims()
    txt = APPLY.read_text(encoding="utf-8")
    cells = []
    cur_mx = None
    cur_tool = None
    for line in txt.splitlines():
        mt = re.match(r"^## MX-C 工具=(SUITE|MTIER)", line)
        if mt:
            cur_mx = "MXC"
            cur_tool = mt.group(1)
            continue
        m = re.match(r"^## (MX-[A-G])(?:\s|（|$)", line)
        if m:
            cur_mx = m.group(1).replace("-", "")
            cur_tool = None
            continue
        if not line.startswith("|") or "---" in line:
            continue
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if cur_mx not in MATRICES or len(cols) < 2:
            continue
        d1codes = dims[cur_mx][0][0]
        d2codes = dims[cur_mx][1][0]
        if cols[0] not in d1codes:
            continue  # 表头行（如 "算法 \ 手段"）
        if len(cols) - 1 < len(d2codes):
            continue
        for j, d2 in enumerate(d2codes):
            d3 = cur_tool if cur_mx == "MXC" else None
            cells.append((cur_mx, cols[0], d2, d3, cols[1 + j]))
    return cells


def case_id(mx, d1, d2, d3):
    parts = [f"TC-{mx}", d1, d2]
    if d3:
        parts.append(d3)
    return "-".join(parts)


def gen_content(mx, d1, d2, d3, dims, env_blocked):
    d1name, d1src = dims[mx][0][1][d1]
    d2name, d2src = dims[mx][1][1][d2]
    d3name = d3src = ""
    if d3 and mx == "MXC":
        d3name, d3src = dims["MXC"][2][1][d3]
    cid = case_id(mx, d1, d2, d3)
    env_note = "\n- **环境阻塞声明**：本格执行依赖外部资产（镜像/GPU/工具链等），未就绪时按测试框架规范 SKIP 不 FAIL，解锁后 hermes 执行" if env_blocked else ""
    if mx == "MXA":
        purpose = f"{d1name} 的{d2name}验证（源：{d1src}）"
        action = METHOD_ACTION[d2]
        steps = (f"# Given 按 {d1src} 的 {d1name} 定义准备参考实现/规格\n"
                 f"# When 执行{action}\n"
                 f"# Then {d1name} 核心机制行为成立（具体数值/不变式断言 enrich 批从源文档派生）\n"
                 f"# And 边界序列不破坏机制语义\n# And 恢复/清理现场")
    elif mx == "MXB":
        purpose = f"{d1name} 形态在{d2name}（{FAILURE_ACTION[d2]}）下的韧性验证"
        steps = (f"# Given {d1name} 栈健康（拓扑/复制/哨兵视图按 07.04/07.05 口径确认）\n"
                 f"# When 注入 {FAILURE_ACTION[d2]}\n"
                 f"# Then 韧性断言成立（转移/不转移语义、零丢失、RTO/RPO 阈值——enrich 批按用例族定值）\n"
                 f"# And 恢复后收敛（视图/复制/哨兵一致性复核）\n# And 稳态复核")
    elif mx == "MXC":
        tool = d3name or "SUITE"
        purpose = f"读写比 {d1name} × 对象 {d2name} × {tool} 基线采集与回归对比"
        steps = (f"# Given lab redis 温机（预热一轮）\n"
                 f"# When {tool} 按 {d1name}/{d2name} 参数采集（--save-baseline 首采，其后对比）\n"
                 f"# Then RPS/延迟落库 baseline.json；复跑偏差 >15% 触发 REGRESSION 需复测确认\n"
                 f"# And 宿主负载记录（共跑栈披露）")
    elif mx == "MXD":
        purpose = f"{d1name} 客户端对 {d2name} 操作族冒烟"
        steps = (f"# Given lab redis 在跑（密码 lab-password）与 {d1name} 工具链\n"
                 f"# When 客户端执行 {d2name} 族代表命令序列（CRUD+边界）\n"
                 f"# Then 每命令响应断言成立（enrich 批按操作族定序列）\n"
                 f"# And 连接清理无泄漏")
    elif mx == "MXE":
        purpose = f"{d1name} 的{d2name}验证（源：{d1src}）"
        action = METHOD_ACTION[d2]
        steps = (f"# Given lab 环境按 {d1src} 推荐配置就位\n"
                 f"# When 执行{action}\n"
                 f"# Then 安全断言成立（拒绝/允许语义；具体断言 enrich 批派生）\n"
                 f"# And 不影响既有服务面\n# And 恢复配置")
    else:  # MXF
        purpose = f"LLM KV Cache {d1name} 的{d2name}验证（源：{d1src}）"
        action = METHOD_ACTION[d2]
        steps = (f"# Given 按 {d1src} 的 {d1name} 机制准备环境（GPU 类前置缺失则 SKIP）\n"
                 f"# When 执行{action}\n"
                 f"# Then 机制行为断言成立（TTFT/命中率/显存——enrich 批定指标）\n"
                 f"# And 结果登记 04.03.15 实测段")
    srcs = [d1src, d2src] + ([d3src] if d3src else [])
    return f"""# {cid} {purpose}

- **用例ID**：{cid} | **优先级**：P1 | **矩阵格**：{mx[:2]}-{mx[2]} / {d1} / {d2}{f' / {d3}' if d3 else ''}
- **自动化**：剧本型（gen 铺底） | **批次**：M2+ gen 2026-11-21
- **运行时**：DOCKER+PODMAN｜ANY（按手段）{env_note}
- **目的**：{purpose}
- **关联**：{' / '.join(srcs)}（维度定义 TSV 行；enrich 批从源文档派生具体数值断言）

## 前置条件

- 按关联源文档准备环境/参考实现；运行时按容器适配规范 §1 探测适配

## 步骤（GWT 五段式）

```text
{steps}
```

## 预期结果

- 各 Then/And 断言成立（具体判定值 enrich 批充实）

## 通过标准

- gen 铺底件的通过标准 = 关联源文档的机制定义；enrich 批补充数值阈值

## 失败纠正与修正指引

1. 环境缺：SKIP 语义登记（测试框架规范铁律），解锁后重跑。
2. 机制断言 fail：先核对参考实现/配置与源文档定义的一致性（定义漂移走文档变更流程）。
3. 本文档为生成器铺底件（Mq gen→enrich 生命周期）；充实=主控 enrich 批或 hermes 执行回填，执行权归 hermes。
"""


def gen():
    dims = load_all_dims()
    rows = registry_rows()
    reg_ids = {r[0] for r in rows}
    created = skipped = 0
    new_rows = []
    for mx, d1, d2, d3, cell in parse_cells():
        if not cell.startswith("●"):
            continue
        if "→" in cell:          # 关联既有用例的归位格
            skipped += 1
            continue
        m = re.search(r"TC-MX[A-G]-[A-Z0-9-]+", cell)
        if m and m.group(0) in reg_ids:   # 已登记（有文件）
            skipped += 1
            continue
        cid = case_id(mx, d1, d2, d3)
        if cid in reg_ids or cid in {r.split("\t")[0] for r in new_rows}:
            skipped += 1
            continue
        env_blocked = "gen·env" in cell or "○E" in cell
        sub = CASES / mx.lower() / d1.lower() / (d2.lower() + (f"-{d3.lower()}" if d3 else ""))
        sub.mkdir(parents=True, exist_ok=True)
        f = sub / f"{cid}.md"
        if not f.exists():
            f.write_text(gen_content(mx, d1, d2, d3, dims, env_blocked), encoding="utf-8")
            created += 1
        note = "gen 铺底" + ("（env-blocked，执行 SKIP 待解锁）" if env_blocked else "")
        new_rows.append(f"{cid}\t{mx}\t{d1}\t{d2}\t{d3 or ''}\tgen\t{note}")
    if new_rows:
        with REG.open("a", encoding="utf-8") as fo:
            for r in new_rows:
                fo.write(r + "\n")
    print(json.dumps({"status": "OK", "created": created, "skipped": skipped,
                      "registry_appended": len(new_rows)}, ensure_ascii=False))
    return 0


def check():
    errs = []
    dims = {}
    for mx, files in MATRICES.items():
        dims[mx] = []
        for fn in files:
            tsv = DIMS / fn
            if not tsv.exists():
                errs.append(f"缺维度定义 {fn}")
                continue
            try:
                dims[mx].append(set(load_dim(tsv)[0]))
            except ValueError as e:
                errs.append(str(e))
                dims[mx].append(set())
    for row in registry_rows():
        if len(row) < 6:
            errs.append(f"注册表行列数 <6: {row}")
            continue
        cid, mx, d1, d2 = row[0], row[1], row[2], row[3]
        if not re.match(r"^TC-MX[A-G]-[A-Z0-9]+(-[A-Z0-9]+)+$", cid):
            errs.append(f"case_id 编码非法: {cid}")
        if mx not in MATRICES:
            errs.append(f"未知矩阵: {mx}（{cid}）")
            continue
        if d1 not in dims[mx][0]:
            errs.append(f"{cid} dim1={d1} 不在 {MATRICES[mx][0]}")
        if d2 not in dims[mx][1]:
            errs.append(f"{cid} dim2={d2} 不在 {MATRICES[mx][1]}")
        if not list(CASES.rglob(f"{cid}.md")):
            errs.append(f"注册表无对应用例文件: {cid}")
    ids = [r[0] for r in registry_rows()]
    if len(ids) != len(set(ids)):
        errs.append("注册表内 case_id 重复")
    dup = existing_case_ids() & set(ids)
    if dup:
        errs.append(f"case_id 与既有用例重复: {sorted(dup)}")
    if APPLY.exists():
        txt = APPLY.read_text(encoding="utf-8")
        for mx in MATRICES:
            head = f"## {mx[:2]}-{mx[2]}"
            if head not in txt:
                errs.append(f"适用矩阵缺矩阵节: {head}")
    else:
        errs.append("缺 适用矩阵.md")
    return errs


def stats():
    board = {}
    if APPLY.exists():
        txt = APPLY.read_text(encoding="utf-8")
        for mx in MATRICES:
            head = f"## {mx[:2]}-{mx[2]}"
            secs = re.findall(rf"{re.escape(head)}.*?(?=## |\Z)", txt, re.S)
            if not secs:
                continue
            cells = []
            env = 0
            for s in secs:
                found = re.findall(r"\|\s*(●|○A|○E|○N|待)(?=[→(·\s|])", s)
                cells += found
                env += len(re.findall(r"gen·env", s))
            board[mx] = {
                "total": len(cells),
                "applicable": cells.count("●"),
                "na_arch": cells.count("○A"),
                "na_env": cells.count("○E"),
                "na_none": cells.count("○N"),
                "pending": cells.count("待"),
                "gen_env_marked": env,
            }
    rows = registry_rows()
    board["_registry"] = {"rows": len(rows),
                          "seed": sum(1 for r in rows if len(r) > 5 and r[5] == "seed"),
                          "gen": sum(1 for r in rows if len(r) > 5 and r[5] == "gen")}
    return board


def main():
    if "--stats" in sys.argv:
        print(json.dumps(stats(), ensure_ascii=False, indent=1))
        return 0
    if "--gen" in sys.argv:
        return gen()
    errs = check()
    if errs:
        print("FAIL " + "; ".join(errs[:10]))
        return 1
    print("PASS 维度/注册表/用例文件/ID 唯一性/适用矩阵齐全性 对账一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
