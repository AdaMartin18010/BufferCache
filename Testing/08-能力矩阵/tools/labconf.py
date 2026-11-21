#!/usr/bin/env python3
# lab.env 读取器（python 侧单一入口；mx_runner 等使用）
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parent.parent.parent / "fixtures" / "lab.env"

DEFAULTS = {
    "BC_RT": "podman",
    "BC_REDIS_IMAGE": "redis:7-alpine",
    "BC_REDIS_PASS": "lab-password",
    "BC_REDIS_HOST": "127.0.0.1",
    "BC_REDIS_PORT": "6379",
    "BC_LAB_CONTAINER": "redis-bench-lab",
    "BC_OUT": "Testing/output",
    "BC_CMD_TIMEOUT": "120",
    "BC_BENCH_TIMEOUT": "300",
}


def load():
    cfg = dict(DEFAULTS)
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            cfg[k.strip()] = v.split(" #", 1)[0].strip()  # 去行尾注释（env 风格）
    return cfg


if __name__ == "__main__":
    import json
    print(json.dumps(load(), ensure_ascii=False, indent=1))
