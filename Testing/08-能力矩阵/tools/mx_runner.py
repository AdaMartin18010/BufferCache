#!/usr/bin/env python3
# 矩阵用例执行器 mx_runner（2026-11-21）：把 08-能力矩阵注册用例中"当前环境可执行"的子集真跑
# 用法: python3 Testing/08-能力矩阵/tools/mx_runner.py [--only TC-ID,TC-ID] [--json]
# 退出码: 0=无 FAIL；1=存在 FAIL
# 判定口径: PASS=实测断言成立 / FAIL=断言破 / SKIP=环境或资产缺失(带原因) / DELEGATED=已由其他门禁覆盖(self_verify/bench_suite)
import json
import subprocess
import sys
import time
import shutil
from pathlib import Path

MX = Path(__file__).resolve().parent.parent
ROOT = MX.parent.parent
REG = MX / "matrix-registry.tsv"
OUT = ROOT / "Testing" / "output" / "mx_runner"
ASSETS = MX / "cases"

# 实验室配置单一事实源（Testing/fixtures/lab.env）；缺失时用文件内默认值
sys.path.insert(0, str(MX / "tools"))
import labconf
_CFG = labconf.load()
LAB = {"addr": f"{_CFG['BC_REDIS_HOST']}:{_CFG['BC_REDIS_PORT']}", "pass": _CFG["BC_REDIS_PASS"],
       "image": _CFG["BC_REDIS_IMAGE"], "container": _CFG["BC_LAB_CONTAINER"],
       "rt_hint": _CFG["BC_RT"]}

RT = None  # 容器运行时探测结果


def rt():
    global RT
    if RT is None:
        RT = shutil.which("podman") or shutil.which("docker") or ""
    return RT


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
    return sh([rt()] + args, timeout)


def lab_redis_up():
    import socket
    h, p = LAB["addr"].split(":")
    try:
        with socket.create_connection((h, int(p)), timeout=2):
            return True
    except OSError:
        return False


def redis_image():
    rc, out = podman(["images", "--format", "{{.Repository}}:{{.Tag}}"])
    return rc == 0 and any("redis" in l for l in out.splitlines())


# ---------------- 执行器实现（case_id → fn() -> (verdict, detail)） ----------------

UNIT_CLASS = {
    "TC-MXA-LRU-UNIT": "TestLRUProperties",
    "TC-MXA-S3FIFO-UNIT": "TestS3FIFOProperties",
    "TC-MXA-FIFO-UNIT": "TestExtendedAlgos",
    "TC-MXA-LFU-UNIT": "TestExtendedAlgos",
    "TC-MXA-SIEVE-UNIT": "TestExtendedAlgos",
    "TC-MXA-2Q-UNIT": "TestExtendedAlgos",
    "TC-MXA-SLRU-UNIT": "TestExtendedAlgos",
    "TC-MXA-ARC-UNIT": "TestExtendedAlgos",
}


def ex_mxa_unit(case_id):
    cls = UNIT_CLASS.get(case_id)
    if not cls:
        return "SKIP", "该算法单测类未映射（enrich 批登记）"
    script = ASSETS / "mxa" / "unit" / "props_test.py"
    rc, out = sh([sys.executable, str(script), cls], timeout=240)
    if rc == 0:
        return "PASS", f"unittest {cls} OK（含 {case_id.split('-')[2]} 参考实现属性断言）"
    return "FAIL", out.strip().splitlines()[-3:]


_MXD_BUILT = {}


def ex_mxd(lang):
    def _run(case_id):
        op = case_id.split("-")[3].lower()          # TC-MXD-GO-HASH → hash
        if not lab_redis_up():
            return "SKIP", f"lab redis {LAB['addr']} 未在跑"
        if lang == "go":
            if not shutil.which("go"):
                return "SKIP", "go 工具链缺失"
            exe = OUT / "mxd_go.exe"
            if "go" not in _MXD_BUILT:
                rc, out = sh(["go", "build", "-o", str(exe), str(ASSETS / "mxd" / "go" / "str" / "main.go")], timeout=300)
                if rc != 0:
                    return "FAIL", "go build: " + out[-200:]
                _MXD_BUILT["go"] = True
            rc, out = sh([str(exe), "-addr", LAB["addr"], "-pass", LAB["pass"], "-ops", op], timeout=120)
        else:
            if not shutil.which("rustc"):
                return "SKIP", "rustc 缺失"
            exe = OUT / "mxd_rs.exe"
            if "rs" not in _MXD_BUILT:
                rc, out = sh(["rustc", str(ASSETS / "mxd" / "rs" / "str" / "main.rs"), "-o", str(exe)], timeout=300)
                if rc != 0:
                    return "FAIL", "rustc: " + out[-200:]
                _MXD_BUILT["rs"] = True
            rc, out = sh([str(exe), "--addr", LAB["addr"], "--pass", LAB["pass"], "--ops", op], timeout=120)
        tail = [l for l in out.splitlines() if l.startswith(("PASS", "FAIL"))]
        return ("PASS", tail[-1] if tail else "OK") if rc == 0 else ("FAIL", out[-200:])
    return _run


def ex_mxd_go_legacy(case_id):
    return ex_mxd("go")(case_id)


def ephemeral(name, extra_args=None, timeout=180):
    """起临时 redis 容器，返回容器名；失败返回 None"""
    extra_args = extra_args or []
    if not rt() or not redis_image():
        return None
    podman(["rm", "-f", name], timeout=30)
    rc, _ = podman(["run", "-d", "--name", name] + extra_args +
                   [LAB["image"], "redis-server", "--requirepass", "lab-password"], timeout=120)
    if rc != 0:
        return None
    for _ in range(30):
        rc, out = podman(["exec", name, "redis-cli", "-a", "lab-password", "--no-auth-warning", "PING"], timeout=20)
        if rc == 0 and "PONG" in out:
            return name
        time.sleep(1)
    return None


def cli(name, *args):
    return podman(["exec", name, "redis-cli", "-a", "lab-password", "--no-auth-warning"] + list(args), timeout=30)


def ex_mxe_auth(case_id):
    c = ephemeral("mxc-auth")
    if not c:
        return "SKIP", "容器运行时或 redis 镜像缺失"
    try:
        _, o1 = podman(["exec", c, "redis-cli", "SET", "k", "v"], timeout=20)
        a1 = "NOAUTH" in o1
        _, o2 = cli(c, "SET", "k1", "v1")
        a2 = o2.strip().endswith("OK")
        cli(c, "ACL", "SETUSER", "ro", "on", ">pw1", "+GET", "~*")
        _, o3 = cli(c, "--user", "ro", "--pass", "pw1", "GET", "k1")
        a3 = "v1" in o3
        rc, o4 = podman(["exec", c, "redis-cli", "--user", "ro", "--pass", "pw1",
                         "--no-auth-warning", "SET", "k2", "v2"], timeout=20)
        a4 = "NOPERM" in o4  # 注意: redis-cli 对服务端错误回复仍返回 rc=0，断言只看消息
        ok = all([a1, a2, a3, a4])
        return ("PASS", f"NOAUTH={a1} AUTH-OK={a2} ACL-GET={a3} ACL-NOPERM={a4}") if ok else \
               ("FAIL", f"NOAUTH={a1} AUTH-OK={a2} ACL-GET={a3} ACL-NOPERM={a4}")
    finally:
        podman(["rm", "-f", c], timeout=60)


def ex_mxe_rename(case_id):
    # 实证修正（2026-11-21 调试）：redis 7 运行时 CONFIG SET rename-command 返回 ERR syntax error——
    # rename-command 只能启动期配置（恰与本用例 边界声明 一致），故用启动参数化容器验证
    if not rt() or not redis_image():
        return "SKIP", "容器运行时或 redis 镜像缺失"
    podman(["rm", "-f", "mxc-rename"], timeout=30)
    rc, _ = podman(["run", "-d", "--name", "mxc-rename", LAB["image"], "redis-server",
                    "--requirepass", "lab-password",
                    "--rename-command", "FLUSHALL", "",
                    "--rename-command", "KEYS", "KEYS_HIDDEN"], timeout=120)
    if rc != 0:
        return "SKIP", "临时容器启动失败"
    try:
        ok_ready = False
        for _ in range(30):
            rc, out = podman(["exec", "mxc-rename", "redis-cli", "-a", "lab-password",
                              "--no-auth-warning", "PING"], timeout=20)
            if rc == 0 and "PONG" in out:
                ok_ready = True
                break
            time.sleep(1)
        if not ok_ready:
            return "FAIL", "容器未就绪"
        _, o1 = podman(["exec", "mxc-rename", "redis-cli", "-a", "lab-password",
                        "--no-auth-warning", "FLUSHALL"], timeout=20)
        a1 = "unknown command" in o1.lower()
        cli("mxc-rename", "SET", "mk", "mv")
        _, o3 = cli("mxc-rename", "KEYS_HIDDEN", "*")
        a2 = "mk" in o3
        return ("PASS", f"FLUSHALL-blocked={a1} KEYS_HIDDEN-works={a2}") if a1 and a2 else \
               ("FAIL", f"FLUSHALL-blocked={a1} KEYS_HIDDEN-works={a2}")
    finally:
        podman(["rm", "-f", "mxc-rename"], timeout=60)


def ex_mxe_net(case_id):
    if not rt() or not redis_image():
        return "SKIP", "容器运行时或 redis 镜像缺失"
    podman(["rm", "-f", "mxc-net-a", "mxc-net-b"], timeout=30)
    podman(["run", "-d", "--name", "mxc-net-a", LAB["image"],
            "redis-server", "--bind", "127.0.0.1", "--requirepass", "lab-password"], timeout=120)
    podman(["run", "-d", "--name", "mxc-net-b", LAB["image"],
            "redis-server", "--protected-mode", "yes"], timeout=120)

    def wait_ready(name, need_auth):
        for _ in range(30):
            args = ["exec", name, "redis-cli"] + (["-a", "lab-password", "--no-auth-warning"] if need_auth else []) + ["PING"]
            rc, out = podman(args, timeout=20)
            if rc == 0 and "PONG" in out:
                return True
            time.sleep(1)
        return False

    def ip_of(name):
        # inspect.IPAddress 在本环境（rootless+pasta）为空——以容器内 hostname -i 为准
        rc, out = podman(["exec", name, "hostname", "-i"], timeout=20)
        ip = out.strip().split()[0] if rc == 0 and out.strip() else None
        return ip

    try:
        ra, rb = wait_ready("mxc-net-a", True), wait_ready("mxc-net-b", False)
        ipa, ipb = ip_of("mxc-net-a"), ip_of("mxc-net-b")
        if not (ra and rb and ipa and ipb):
            return "FAIL", f"A-ready={ra} B-ready={rb} A-ip={ipa} B-ip={ipb}"
        if ipa == ipb:
            # 实证（2026-11-21）：rootless+pasta 网络下各容器同址（192.168.127.2），容器间不可互通，
            # name DNS 亦缺——两条网络面断言在本环境不可执行（docker/全栈网络宿主可执行，用例保留）
            return "SKIP", f"pasta 网络容器间不可互通（A/B 同址 {ipa}），NET-LIVE 双断言需 docker 类网络宿主"
        # A: bind 127.0.0.1 → 同网络 sidecar 按 IP 直连应连接被拒（只监听容器回环）
        rc, o1 = podman(["run", "--rm", LAB["image"], "sh", "-c",
                         f"timeout 5 redis-cli -h {ipa} -a lab-password --no-auth-warning PING"], timeout=60)
        a1 = rc != 0 and ("Could not connect" in o1 or "refused" in o1 or rc == 124)
        # B: protected-mode + 无密码 → 同网络 sidecar 按 IP 直连应 DENIED
        rc, o2 = podman(["run", "--rm", LAB["image"], "sh", "-c",
                         f"timeout 5 redis-cli -h {ipb} PING"], timeout=60)
        a2 = "DENIED" in o2
        return ("PASS", f"bind-loopback-blocked={a1} protected-mode-denied={a2}") if a1 and a2 else \
               ("FAIL", f"bind-loopback-blocked={a1} protected-mode-denied={a2}")
    finally:
        podman(["rm", "-f", "mxc-net-a", "mxc-net-b"], timeout=60)


EXECUTORS = {
    "TC-MXA-LRU-UNIT": ex_mxa_unit,
    "TC-MXA-S3FIFO-UNIT": ex_mxa_unit,
    "TC-MXA-FIFO-UNIT": ex_mxa_unit,
    "TC-MXA-LFU-UNIT": ex_mxa_unit,
    "TC-MXA-SIEVE-UNIT": ex_mxa_unit,
    "TC-MXA-2Q-UNIT": ex_mxa_unit,
    "TC-MXA-SLRU-UNIT": ex_mxa_unit,
    "TC-MXA-ARC-UNIT": ex_mxa_unit,
    "TC-MXD-GO-STR": ex_mxd("go"),
    "TC-MXD-GO-HASH": ex_mxd("go"),
    "TC-MXD-GO-LIST": ex_mxd("go"),
    "TC-MXD-GO-ZSET": ex_mxd("go"),
    "TC-MXD-GO-STREAM": ex_mxd("go"),
    "TC-MXD-GO-BITMAP": ex_mxd("go"),
    "TC-MXD-GO-EXPIRE": ex_mxd("go"),
    "TC-MXD-GO-TXLUA": ex_mxd("go"),
    "TC-MXD-RS-STR": ex_mxd("rs"),
    "TC-MXD-RS-HASH": ex_mxd("rs"),
    "TC-MXD-RS-LIST": ex_mxd("rs"),
    "TC-MXD-RS-ZSET": ex_mxd("rs"),
    "TC-MXD-RS-STREAM": ex_mxd("rs"),
    "TC-MXD-RS-BITMAP": ex_mxd("rs"),
    "TC-MXD-RS-EXPIRE": ex_mxd("rs"),
    "TC-MXD-RS-TXLUA": ex_mxd("rs"),
    "TC-MXE-AUTH-LIVE": ex_mxe_auth,
    "TC-MXE-RENAME-LIVE": ex_mxe_rename,
    "TC-MXE-NET-LIVE": ex_mxe_net,
}

# 委托判定（已由其他门禁覆盖的格，不重复执行）
DELEGATED = {
    "MXE": ("STATIC 列已由 self_verify ops/security 组（TC-OPS-003/SEC-001）覆盖",),
    "MXG": ("40 格全部由 self_verify docs/links 组 + 语义抽检覆盖",),
}
DELEGATED_SUFFIX = {"STATIC": "self_verify ops/security 组覆盖", }


def main():
    only = None
    if "--only" in sys.argv:
        only = set(sys.argv[sys.argv.index("--only") + 1].split(","))
    OUT.mkdir(parents=True, exist_ok=True)
    results = []
    for line in REG.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#") or line.startswith("case_id"):
            continue
        p = line.split("\t")
        cid, mx = p[0], p[1]
        if only and cid not in only:
            continue
        t0 = time.time()
        if cid in EXECUTORS:
            verdict, detail = EXECUTORS[cid](cid)
        elif mx == "MXE" and p[3] == "STATIC":
            verdict, detail = "DELEGATED", DELEGATED["MXE"][0]
        elif mx == "MXG":
            verdict, detail = "DELEGATED", DELEGATED["MXG"][0]
        elif mx == "MXC" and p[4] == "SUITE":
            verdict, detail = "DELEGATED", "bench_suite 执行（A1 已建温基线，--save-baseline/--compare）"
        else:
            verdict, detail = "SKIP", "无执行器实现或环境阻塞（enrich/M3 解锁后接入）"
        results.append({"case_id": cid, "mx": mx, "verdict": verdict,
                        "detail": detail, "duration_s": round(time.time() - t0, 1)})
    n = {v: sum(1 for r in results if r["verdict"] == v) for v in ("PASS", "FAIL", "SKIP", "DELEGATED")}
    ts = time.strftime("%Y%m%d_%H%M%S")
    (OUT / f"result_{ts}.json").write_text(
        json.dumps({"ts": ts, "summary": n, "results": results}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{'用例ID':<28}{'判定':<11}{'耗时':<7}详情")
    for r in results:
        print(f"{r['case_id']:<28}{r['verdict']:<11}{r['duration_s']:<7}{r['detail'][:70]}")
    print(f"\nSUMMARY pass={n['PASS']} fail={n['FAIL']} skip={n['SKIP']} delegated={n['DELEGATED']}  → Testing/output/mx_runner/result_{ts}.json")
    return 1 if n["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
