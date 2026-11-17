#!/usr/bin/env python3
"""
BufferCache 标准化基准套件（TC-BENCH-005）

把"一发式 redis-benchmark"升级为场景化矩阵 + 基线对比：
- 场景矩阵：读写比 × 数据规模 × 热点集中度（对齐 01.05.04 §6 的负载模型）
- 基线入库：results 存 JSON，与历史基线对比，偏差 >15% 报告疑似回归
- 环境适配：无 redis-server 实例时自动 SKIP（CI/本地均可跑）

用法：
    python scripts/benchmark/suite/bench_suite.py                 # 全场景（需本地 6379）
    python scripts/benchmark/suite/bench_suite.py --scenarios get_heavy --save-baseline
    python scripts/benchmark/suite/bench_suite.py --compare baseline.json

对应文档: docs/07-运维与部署/07.05-集群管理/07.05.04-集群容量规划.md §3 实测基线
"""

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
RESULT_DIR = REPO_ROOT / "Testing" / "output" / "bench_suite"
BASELINE_FILE = RESULT_DIR / "baseline.json"
REGRESS_THRESHOLD = 0.15  # C 级经验阈值：基准波动 >15% 视为疑似回归，需复测确认

# 场景矩阵：名 = 读比_大小_热点
SCENARIOS = {
    "balanced_small":  ["-r", "0.5", "-d", "256"],    # 读写均衡小对象
    "get_heavy_small": ["-r", "0.9", "-d", "256"],    # 读多写少（Web 典型）
    "set_heavy_small": ["-r", "0.2", "-d", "256"],    # 写密集（计数器）
    "get_heavy_large": ["-r", "0.9", "-d", "8192"],   # 大对象读（详情页）
}


def redis_available(host="127.0.0.1", port=6379, timeout=2.0):
    import socket
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def run_bench(name, args, host, port, password, requests):
    cmd = ["redis-benchmark", "-h", host, "-p", str(port), "-n", str(requests), "-c", "50", "-q", "-t", "set,get"] + args
    if password:
        cmd += ["-a", password, "--no-auth-warning"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300,
                           encoding="utf-8", errors="replace")
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return {"error": str(e)}
    out = r.stdout or ""
    res = {"scenario": name, "ts": time.strftime("%Y-%m-%d %H:%M:%S")}
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("SET:"):
            res["set_rps"] = float(line.split()[1].replace("requests per second,", "").strip() or 0)
        elif line.startswith("GET:"):
            res["get_rps"] = float(line.split()[1].replace("requests per second,", "").strip() or 0)
    for key in ("set_rps", "get_rps"):
        if key not in res:
            res.setdefault("error", f"输出缺少 {key}: {out[:200]}")
    return res


def compare_to_baseline(results, baseline_path, threshold):
    try:
        baseline = json.loads(Path(baseline_path).read_text(encoding="utf-8"))
    except Exception as e:
        return [f"基线读取失败: {e}"], []
    regressions, notes = [], []
    for r in results:
        b = baseline.get(r.get("scenario"))
        if not b or "error" in r:
            continue
        for k in ("set_rps", "get_rps"):
            cur, old = r.get(k), b.get(k)
            if not cur or not old:
                continue
            dev = (cur - old) / old
            notes.append(f"{r['scenario']}.{k}: {cur:.0f} vs 基线 {old:.0f} ({dev:+.1%})")
            if dev < -threshold:
                regressions.append(f"疑似回归 {r['scenario']}.{k}: {dev:+.1%}（阈值 -{threshold:.0%}）")
    return regressions, notes


def main():
    ap = argparse.ArgumentParser(description="缓存基准套件")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=6379)
    ap.add_argument("--password", default="")
    ap.add_argument("--requests", type=int, default=20000)
    ap.add_argument("--scenarios", nargs="*", default=list(SCENARIOS),
                    help=f"可选: {', '.join(SCENARIOS)}")
    ap.add_argument("--save-baseline", action="store_true", help="结果存为新基线")
    ap.add_argument("--compare", help="与指定基线 JSON 对比（默认对比内置基线）")
    args = ap.parse_args()

    if not shutil.which("redis-benchmark"):
        print(json.dumps({"status": "SKIP", "reason": "未安装 redis-benchmark"}, ensure_ascii=False))
        return 2
    if not redis_available(args.host, args.port):
        print(json.dumps({"status": "SKIP", "reason": f"{args.host}:{args.port} 无 Redis 实例"}, ensure_ascii=False))
        return 2

    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for name in args.scenarios:
        if name not in SCENARIOS:
            print(f"未知场景 {name}，跳过")
            continue
        r = run_bench(name, SCENARIOS[name], args.host, args.port, args.password, args.requests)
        results.append(r)
        tag = "ERROR" if "error" in r else "OK"
        print(f"[{tag}] {name}: set={r.get('set_rps', '-')} get={r.get('get_rps', '-')}")

    out_file = RESULT_DIR / f"result_{time.strftime('%Y%m%d_%H%M%S')}.json"
    out_file.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.save_baseline:
        BASELINE_FILE.write_text(json.dumps({r["scenario"]: r for r in results if "error" not in r},
                                            ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"基线已存: {BASELINE_FILE}")
        return 0

    baseline_path = args.compare or BASELINE_FILE
    if Path(baseline_path).exists():
        regressions, notes = compare_to_baseline(results, baseline_path, REGRESS_THRESHOLD)
        for n in notes:
            print("  " + n)
        for g in regressions:
            print("  ⚠ " + g)
        status = "REGRESSION" if regressions else "PASS"
        print(json.dumps({"status": status, "detail": out_file.name}, ensure_ascii=False))
        return 1 if regressions else 0
    print(json.dumps({"status": "PASS", "note": "无基线可对比", "detail": out_file.name}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
