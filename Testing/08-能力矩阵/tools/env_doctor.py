#!/usr/bin/env python3
# env_doctor 环境治理器（2026-11-21 hermes 就绪包 2.0）——自检/监测/更新/总结/自修正 五合一
# 约束落地：podman 唯一 + 镜像钉"最新成熟发布版" + 可逆自修正。
# 用法:
#   env_doctor.py check [--fix]     自检：运行时/镜像在盘/lab 容器健康/端口/磁盘；--fix 仅做可逆动作（start 容器）
#   env_doctor.py monitor           监测：钉版镜像上游最新 stable 比对（网络不可达诚实 SKIP）+ 容器健康 + 基线新鲜度
#   env_doctor.py update --image X  更新流：拉新镜像→改 lab.env 钉版→重建 lab 容器→（--bench 时）重建基线
#   env_doctor.py summary           总结：一页环境状态报告（镜像表/健康/待更新/基线日期）落 Testing/output/
# RC: 0=全绿；1=存在 FAIL；2=用法错。产物 Testing/output/env_doctor/
import json
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

MX = Path(__file__).resolve().parent.parent
ROOT = MX.parent.parent
sys.path.insert(0, str(MX / "tools"))
import labconf

C = labconf.load()
OUT = ROOT / C["BC_OUT"] / "env_doctor"
OUT.mkdir(parents=True, exist_ok=True)
TS = time.strftime("%Y%m%d_%H%M%S")


def sh(cmd, timeout=120):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace")
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, "TIMEOUT"
    except FileNotFoundError as e:
        return 127, str(e)


def podman(args, timeout=120):
    return sh([C["BC_RT"]] + args, timeout)


def pinned_images():
    """lab.env 中 BC_IMG_* 钉版清单（排除 META 键）"""
    return {k: v for k, v in C.items() if k.startswith("BC_IMG_") and k != "BC_IMG_REDIS_TARGET_MAJOR"}


def lab_key(k):
    return {"BC_IMG_REDIS": "redis"}.get(k, k.replace("BC_IMG_", "").lower())


# ---------------- check（自检 + --fix 可逆修正） ----------------

def do_check(fix=False):
    rows = []

    def add(item, verdict, detail):
        rows.append({"item": item, "verdict": verdict, "detail": detail})

    # 1) 运行时：podman 唯一
    rc, out = sh([C["BC_RT"], "version", "--format", "{{.Client.Version}}"])
    if rc != 0:
        add("运行时 podman", "FAIL", "podman 不可用（唯一受支持运行时；缺→全 L2 SKIP）")
        return rows
    ver = out.strip().split()[0] if out.strip() else "?"
    add("运行时 podman", "PASS", f"version {ver}")

    # 2) 镜像在盘（:latest 未钉版给 WARN——成熟版策略要求钉 major.minor）
    rc, out = podman(["images", "--format", "{{.Repository}}:{{.Tag}}"])
    local = out.splitlines() if rc == 0 else []
    for k, img in pinned_images().items():
        name = lab_key(k)
        tag = img.split(":", 1)[-1]
        present = any(l.split(":", 1)[-1] == tag and img.split(":")[0] in l for l in local)
        if not present:
            add(f"镜像 {img}", "WARN", "未在盘（相关用例 SKIP；获取=update 流或镜像源恢复）")
        elif tag == "latest":
            add(f"镜像 {img}", "WARN", ":latest 未钉版（违反成熟版策略→monitor 查 stable 后 update 钉版）")
        else:
            add(f"镜像 {img}", "PASS", "在盘且已钉版")

    # 3) lab 容器健康 + --fix 可逆自修正
    rc, out = podman(["ps", "--format", "{{.Names}} {{.Status}}"])
    if C["BC_LAB_CONTAINER"] in out:
        add("lab 容器", "PASS", "在跑")
    else:
        rc2, out2 = podman(["ps", "-a", "--format", "{{.Names}}"])
        if C["BC_LAB_CONTAINER"] in out2 and fix:
            podman(["start", C["BC_LAB_CONTAINER"]], timeout=120)
            time.sleep(3)
            rc3, out3 = podman(["exec", C["BC_LAB_CONTAINER"], "redis-cli", "-a", C["BC_REDIS_PASS"],
                                "--no-auth-warning", "PING"])
            add("lab 容器", "PASS" if rc3 == 0 else "FAIL",
                "自修正：已 start" + (" 且 PONG" if rc3 == 0 else " 但 PING 失败"))
        elif C["BC_LAB_CONTAINER"] in out2:
            add("lab 容器", "FAIL", "存在但停（可逆修正可用 --fix start）")
        else:
            add("lab 容器", "WARN", "未创建（基线类用例 SKIP；创建命令见 A1 执行记录）")

    # 4) 端口连通
    import socket
    try:
        with socket.create_connection((C["BC_REDIS_HOST"], int(C["BC_REDIS_PORT"])), timeout=2):
            add("端口连通", "PASS", f'{C["BC_REDIS_HOST"]}:{C["BC_REDIS_PORT"]}')
    except OSError as e:
        add("端口连通", "FAIL", str(e))

    # 5) 磁盘余量（>5G 为绿）
    rc, out = sh(["df", "-m", str(ROOT)])
    if rc == 0:
        avail = int(out.splitlines()[-1].split()[-3])
        add("磁盘余量", "PASS" if avail > 5120 else "WARN", f"{avail} MB 可用")
    return rows


# ---------------- monitor（监测：上游 stable 比对 + 健康 + 基线新鲜度） ----------------

def upstream_latest(image):
    """尽力查询上游最新 stable tag；不可达返回 None（诚实 SKIP）"""
    repo, _, tag = image.partition(":")
    try:
        if "prometheus" in repo:
            url = "https://quay.io/api/v1/repository/prometheus/prometheus/tag/?limit=100"
            with urllib.request.urlopen(url, timeout=15) as r:
                tags = json.load(r)
            cands = [t["name"] for t in tags.get("tags", [])
                     if re.fullmatch(r"v?\d+\.\d+\.\d+", t["name"])]
            return sorted(cands, key=lambda s: [int(x) for x in re.findall(r"\d+", s)])[-1] if cands else None
        # 其余镜像走 hub.docker.com API（web API，与被拒的 registry-1 不同源）
        ns = "library" if "/" not in repo else repo.split("/")[0]
        name = repo.split("/")[-1]
        url = f"https://hub.docker.com/v2/repositories/{ns}/{name}/tags?page_size=100"
        req = urllib.request.Request(url, headers={"User-Agent": "env_doctor/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.load(r)
        cands = [t["name"] for t in data.get("results", [])
                 if re.fullmatch(r"\d+\.\d+(\.\d+)?(-alpine)?", t["name"]) and "rc" not in t["name"] and "beta" not in t["name"]]
        return sorted(cands, key=lambda s: [int(x) for x in re.findall(r"\d+", s)])[-1] if cands else None
    except Exception as e:
        return None


def do_monitor():
    rows = []
    for k, img in pinned_images().items():
        name = lab_key(k)
        cur = img.split(":", 1)[-1]
        latest = upstream_latest(img)
        if latest is None:
            rows.append({"image": img, "verdict": "SKIP", "detail": "上游查询不可达（网络/源策略）；钉版维持现状"})
        elif cur == "latest":
            rows.append({"image": img, "verdict": "WARN", "detail": f":latest 未钉版；上游最新 stable ≈ {latest} → update 流钉版"})
        elif latest.startswith(cur.split("-")[0]) or latest == cur:
            rows.append({"image": img, "verdict": "PASS", "detail": f"钉版 {cur} 处最新稳定线（上游 {latest}）"})
        else:
            rows.append({"image": img, "verdict": "WARN", "detail": f"上游更新：{cur} → {latest}（成熟版→可排 update）"})
    # 基线新鲜度
    bl = ROOT / C["BC_OUT"] / "bench_suite" / "baseline.json"
    if bl.exists():
        age = (time.time() - bl.stat().st_mtime) / 86400
        rows.append({"image": "baseline.json", "verdict": "PASS" if age < 30 else "WARN",
                     "detail": f"基线 {age:.0f} 天前（镜像升级后须重建）"})
    else:
        rows.append({"image": "baseline.json", "verdict": "WARN", "detail": "无基线（A1 已跑则应在 Testing/output/bench_suite/）"})
    return rows


# ---------------- update（更新流） ----------------

def do_update(image, bench=False):
    print(f"[update] 拉取 {image} ...")
    rc, out = podman(["pull", image], timeout=600)
    if rc != 0:
        print(f"FAIL pull: {out[-300:]}")
        return 1
    print("[update] 更新 lab.env 钉版 ...")
    envf = labconf.ENV_FILE
    t = envf.read_text(encoding="utf-8")
    repo = image.split(":")[0]
    for k, v in pinned_images().items():
        if v.split(":")[0] == repo:
            t = re.sub(rf"^{k}=.*$", f"{k}={image}", t, flags=re.M)
    envf.write_text(t, encoding="utf-8")
    print("[update] 重建 lab 容器 ...")
    podman(["rm", "-f", C["BC_LAB_CONTAINER"]], timeout=60)
    rc, _ = podman(["run", "-d", "--name", C["BC_LAB_CONTAINER"],
                    "-p", f'{C["BC_REDIS_PORT"]}:6379', "-v", "redis-bench-data:/data",
                    image, "redis-server", "--appendonly", "yes", "--requirepass", C["BC_REDIS_PASS"]], timeout=180)
    if rc != 0:
        print("FAIL 容器重建")
        return 1
    if bench:
        print("[update] 重建基准（bench_suite --save-baseline）...")
        rc, out = sh([sys.executable, str(ROOT / "scripts/benchmark/suite/bench_suite.py"),
                      "--host", C["BC_REDIS_HOST"], "--port", C["BC_REDIS_PORT"], "--password", C["BC_REDIS_PASS"],
                      "--bench-cmd", f'{C["BC_RT"]} exec {C["BC_LAB_CONTAINER"]} redis-benchmark',
                      "--save-baseline"], timeout=600)
        print(("[update] 基线已重建" if rc == 0 else f"[update] 基线重建失败: {out[-200:]}"))
    print("[update] 完成。受影响用例：MX-C 全格 + A1 关联记录——须复跑 mx_runner 相关格并回填执行记录")
    return 0


# ---------------- summary（总结页） ----------------

def do_summary():
    chk = do_check()
    mon = do_monitor()
    report = {"ts": TS, "check": chk, "monitor": mon}
    f = OUT / f"summary_{TS}.json"
    f.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{'项':<34}{'判定':<8}详情")
    for r in chk:
        print(f"{r['item']:<34}{r['verdict']:<8}{r['detail'][:60]}")
    print("--- 监测 ---")
    for r in mon:
        print(f"{r['image']:<34}{r['verdict']:<8}{r['detail'][:60]}")
    n = {v: sum(1 for r in chk + mon if r["verdict"] == v) for v in ("PASS", "FAIL", "WARN", "SKIP")}
    print(f"\nSUMMARY check+monitor: pass={n['PASS']} fail={n['FAIL']} warn={n['WARN']} skip={n['SKIP']} → {f}")
    return 1 if n["FAIL"] else 0


def main():
    args = sys.argv[1:]
    if not args:
        print("用法: env_doctor.py check [--fix] | monitor | update --image <img> [--bench] | summary")
        return 2
    cmd = args[0]
    if cmd == "check":
        rows = do_check(fix="--fix" in args)
        for r in rows:
            print(f"{r['verdict']:<6}{r['item']:<30}{r['detail']}")
        (OUT / f"check_{TS}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        return 1 if any(r["verdict"] == "FAIL" for r in rows) else 0
    if cmd == "monitor":
        rows = do_monitor()
        for r in rows:
            print(f"{r['verdict']:<6}{r['image']:<34}{r['detail']}")
        (OUT / f"monitor_{TS}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        return 0
    if cmd == "update":
        if "--image" not in args:
            print("update 需要 --image <钉版镜像>")
            return 2
        return do_update(args[args.index("--image") + 1], bench="--bench" in args)
    if cmd == "summary":
        return do_summary()
    return 2


if __name__ == "__main__":
    sys.exit(main())
