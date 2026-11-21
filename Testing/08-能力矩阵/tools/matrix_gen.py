#!/usr/bin/env python3
# 能力矩阵生成器与一致对账门（M1，2026-11-21）
# 用法:
#   matrix_gen.py --check   一致对账（self_verify 矩阵组门禁）:
#                           ① 维度 TSV 结构合法 ② 注册表行维度取值合法 ③ 注册表 case 文件存在
#                           ④ ID 全局唯一（00-05 职能域 + 08 矩阵层 + 注册表） ⑤ 适用矩阵含全部 7 矩阵
#   matrix_gen.py --stats   覆盖看板数据（各矩阵格数/待补数/●数/登记数）→ stdout JSON
#   matrix_gen.py --gen     从适用矩阵 ●格批量铺底用例骨架（M3 启用；当前仅骨架含 GWT 占位）
# RC: 0=PASS；1=FAIL；2=SKIP（无 python3 由调用方处理）
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

CELL_RE = re.compile(r"^(●|○A|○E|○N|待)\b|^(●|○A|○E|○N|待)$")


def load_dim(tsv):
    codes = []
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
    return codes


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
        for f in base.rglob("TC-*.md"):
            m = re.match(r"(TC-[A-Za-z0-9-]+?)(?:-\d+)?\.md$", f.name)
            if m:
                ids.add(m.group(1))
    return ids


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
                dims[mx].append(set(load_dim(tsv)))
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
        hit = list(CASES.rglob(f"{cid}.md"))
        if not hit:
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
            for s in secs:
                # 单元格形态：纯标记（"待"）/ 标记+关联（"●→FORM-001"/"●(B3)"）/ 标记+理由（"○E 镜像缺"）
                cells += re.findall(r"\|\s*(●|○A|○E|○N|待)(?=[→(\s|])", s)
            board[mx] = {
                "total": len(cells),
                "applicable": cells.count("●"),
                "na_arch": cells.count("○A"),
                "na_env": cells.count("○E"),
                "na_none": cells.count("○N"),
                "pending": cells.count("待"),
            }
    rows = registry_rows()
    board["_registry"] = {"rows": len(rows), "seed": sum(1 for r in rows if len(r) > 5 and r[5] == "seed")}
    return board


def main():
    if "--stats" in sys.argv:
        print(json.dumps(stats(), ensure_ascii=False, indent=1))
        return 0
    if "--gen" in sys.argv:
        print(json.dumps({"status": "SKIP", "reason": "--gen 于 M3 启用（先由 M2 种子批人工精修 P0 格定版模板）"}, ensure_ascii=False))
        return 2
    errs = check()
    if errs:
        print("FAIL " + "; ".join(errs[:10]))
        return 1
    print("PASS 维度/注册表/用例文件/ID 唯一性/适用矩阵齐全性 对账一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
