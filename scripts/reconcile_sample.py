#!/usr/bin/env python3
"""
缓存-数据源对账采样器（04.04.11 的最小可执行工具）

输入 key 名单（或随机采样），双端读取比对（缓存 vs 数据源回调），
输出不一致列表 + 比率 + 置信区间。数据源回调由调用方注入（本脚本
提供 Redis↔文件字典的演示模式与自定义回调接口）。

用法（演示模式：缓存=Redis，数据源=本地 JSON 文件）：
    python scripts/reconcile_sample.py --redis 127.0.0.1:6379 --password lab-password \
        --source demo_source.json --sample 1000

    # demo_source.json: {"key1": "value1", ...}（模拟 DB 真值）

编程使用：
    from scripts.reconcile_sample import reconcile
    drifts, rate, ci = reconcile(redis_cli, db_get, keys)   # db_get: key -> value
"""

import argparse
import json
import math
import random
import sys
from pathlib import Path


def reconcile(cache_get, source_get, keys):
    """双端比对。返回 (漂移key列表, 不一致率, 95%CI半宽)。"""
    drifts = []
    for k in keys:
        cv = cache_get(k)
        sv = source_get(k)
        # 语义：缓存缺失不算漂移（正常 miss）；值不等才算
        if cv is not None and sv is not None and cv != sv:
            drifts.append(k)
        elif cv is not None and sv is None:
            drifts.append(k)   # 缓存有而源已删（典型漂移）
    n = max(len(keys), 1)
    p = len(drifts) / n
    ci = 1.96 * math.sqrt(p * (1 - p) / n) if n > 0 else 0
    return drifts, p, ci


def demo_mode(args):
    import socket

    def parse_addr(addr):
        h, p = addr.rsplit(":", 1)
        return h, int(p)

    host, port = parse_addr(args.redis)

    class TinyRedis:
        """最小 RESP 客户端（GET only），免第三方依赖。"""

        def __init__(self, h, p, password=None):
            self.addr = (h, p)
            self.password = password

        def _roundtrip(self, *cmds):
            with socket.create_connection(self.addr, timeout=3) as s:
                if self.password:
                    s.sendall(self._enc("AUTH", self.password))
                    s.recv(128)
                s.sendall(self._enc(*cmds))
                return self._parse(s)

        @staticmethod
        def _enc(*parts):
            out = [f"*{len(parts)}\r\n".encode()]
            for p in parts:
                b = str(p).encode()
                out.append(f"${len(b)}\r\n".encode() + b + b"\r\n")
            return b"".join(out)

        @staticmethod
        def _parse(s):
            head = s.recv(1)
            if head == b"$":
                ln = int(s.recv(64).split(b"\r\n", 1)[0])
                if ln == -1:
                    return None
                data = b""
                while len(data) < ln + 2:
                    data += s.recv(ln + 2 - len(data))
                return data[:ln].decode(errors="replace")
            s.recv(256)
            return None

        def get(self, k):
            return self._roundtrip("GET", k)

    source = json.loads(Path(args.source).read_text(encoding="utf-8"))
    r = TinyRedis(host, port, args.password or None)

    all_keys = list(source.keys())
    random.Random(args.seed).shuffle(all_keys)
    keys = all_keys[:args.sample] if args.sample else all_keys

    drifts, p, ci = reconcile(r.get, lambda k: source.get(k), keys)
    print(f"采样 {len(keys)}/{len(all_keys)} keys")
    print(f"漂移 {len(drifts)} 个，不一致率 {p:.4%}（95%CI ±{ci:.4%}）")
    for k in drifts[:20]:
        print(f"  DRIFT: {k}")
    # 判据输出（04.04.11 三级）
    if p > 0.05:
        print("判定: 系统性故障级漂移（>5%）→ 应急预案")
        return 1
    if p > 0.01:
        print("判定: 告警级漂移（>1%）→ 根因调查")
        return 1
    if p > 0.001:
        print("判定: 自动刷新级漂移（>0.1%）→ 触发修复")
        return 1
    print("判定: 正常范围")
    return 0


def main():
    ap = argparse.ArgumentParser(description="缓存-数据源对账采样器")
    ap.add_argument("--redis", help="Redis 地址 host:port（演示模式必填）")
    ap.add_argument("--password", default="")
    ap.add_argument("--source", help="数据源 JSON 文件（key->value，演示模式）")
    ap.add_argument("--sample", type=int, default=1000, help="采样数（0=全量）")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    if args.redis and args.source:
        return demo_mode(args)
    print("演示模式需 --redis 与 --source；编程使用见 docstring")
    return 2


if __name__ == "__main__":
    sys.exit(main())
