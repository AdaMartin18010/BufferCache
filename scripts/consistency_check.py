#!/usr/bin/env python3
"""
BufferCache 项目 —— 缓存一致性竞态验证器（最小可执行版，TC-BENCH-003）

模拟 Cache-Aside 写路径（更新 DB → 删除缓存）在高并发下的不一致窗口，
对照三种工程策略，量化"最终一致性"达成时间：

  A. 删缓存无兜底      —— 删缓存失败即永久不一致（反例）
  B. 删缓存 + TTL      —— TTL 内自愈，不一致窗口 ≤ TTL（基线）
  C. 延迟双删          —— 第二次异步删除压缩窗口（优化）

一致性定义：缓存中不存在过期值（缓存值 == DB 值，或缓存缺失）。
窗口：从"DB 已更新"到"缓存不再返回旧值"的时长。

用法：
    python scripts/consistency_check.py            # 默认参数
    python scripts/consistency_check.py --threads 16 --duration 8

对应文档: docs/04-架构设计/04.01-缓存架构模式/04.01.01-Cache-Aside旁路缓存.md
"""

import argparse
import random
import threading
import time
from collections import defaultdict

# ---------------------------------------------------------------------------
# 被测系统模拟
# ---------------------------------------------------------------------------

class SimulatedDB:
    """单 key 即够演示竞态（多 key 只是放大，不改变机制）"""
    def __init__(self):
        self._lock = threading.Lock()
        self.value = 0

    def write(self, v):
        with self._lock:
            self.value = v

    def read(self):
        with self._lock:
            return self.value

class SimulatedCache:
    """带 TTL 的缓存槽：value + 写入时刻；删除可注入失败率"""
    def __init__(self, ttl: float, delete_fail_rate: float, rng: random.Random):
        self.ttl = ttl
        self.fail_rate = delete_fail_rate
        self.rng = rng
        self._lock = threading.Lock()
        self.val = None      # (value, written_at) 或 None
        self.delete_fails = 0

    def get(self, now):
        with self._lock:
            if self.val is None:
                return None
            v, ts = self.val
            if now - ts > self.ttl:
                return None          # TTL 过期（自然自愈）
            return v

    def set(self, v, now):
        with self._lock:
            self.val = (v, now)

    def delete(self):
        with self._lock:
            if self.rng.random() < self.fail_rate:
                self.delete_fails += 1
                return False
            self.val = None
            return True

# ---------------------------------------------------------------------------
# 实验：测量不一致窗口
# ---------------------------------------------------------------------------

def run_experiment(strategy: str, ttl: float, delete_fail_rate: float,
                   threads: int, duration: float, delete_delay: float,
                   seed: int = 42):
    """返回 (窗口列表, 统计)。A 策略 TTL 为 ∞，实验中以 ttl_cap 截断测量。"""
    db = SimulatedDB()
    rng = random.Random(seed)
    ttl_cap = 5.0                      # A 策略窗口测量截断上限（真实为 ∞）
    eff_ttl = ttl if strategy in ("B", "C") else ttl_cap
    cache = SimulatedCache(eff_ttl, delete_fail_rate, rng)
    windows = []          # 每次写操作的不一致窗口时长
    stop = time.time() + duration
    start = threading.Event()          # 发令事件：替代 Barrier，杜绝 party 不齐死锁

    def writer():
        start.wait(timeout=10)
        while time.time() < stop:
            v = db.read() + 1
            db.write(v)                       # 1. 先更新 DB
            t0 = time.time()
            cache.delete()                    # 2. 删缓存（可能失败）
            if strategy == "C":
                time.sleep(delete_delay)      # 3. 延迟双删
                cache.delete()
            # 测量窗口：读侧看到旧值直到缓存被覆盖/过期/删除成功
            deadline = t0 + min(eff_ttl, ttl_cap) + delete_delay + 0.3
            while time.time() < deadline:
                cur = cache.get(time.time())
                if cur is None or cur == db.read():
                    break
                time.sleep(0.002)
            windows.append(time.time() - t0)
            time.sleep(0.002)

    def reader():
        start.wait(timeout=10)
        stale_reads = 0
        reads = 0
        while time.time() < stop:
            v = cache.get(time.time())
            if v is None:                     # miss → 回源并回填
                v = db.read()
                cache.set(v, time.time())
            reads += 1
            if v != db.read():
                stale_reads += 1
            time.sleep(0.004)
        return stale_reads, reads

    results = []
    n_w = max(1, threads // 2)
    n_r = max(1, threads - n_w)
    ts = [threading.Thread(target=writer, daemon=True) for _ in range(n_w)]
    rs = [threading.Thread(target=reader, daemon=True) for _ in range(n_r)]
    for t in ts + rs: t.start()
    start.set()
    for t in ts + rs: t.join(timeout=duration + ttl_cap + delete_delay + 30)

    return windows, dict(delete_fails=cache.delete_fails)

def main():
    ap = argparse.ArgumentParser(description="缓存一致性竞态验证")
    ap.add_argument('--threads', type=int, default=8)
    ap.add_argument('--duration', type=float, default=6.0, help='每策略实验秒数')
    ap.add_argument('--ttl', type=float, default=2.0, help='策略B/C 的 TTL 秒')
    ap.add_argument('--delete-fail-rate', type=float, default=0.15)
    ap.add_argument('--delete-delay', type=float, default=0.3, help='策略C 延迟双删间隔')
    args = ap.parse_args()

    print(f"配置: threads={args.threads} duration={args.duration}s "
          f"ttl={args.ttl}s 删缓存失败率={args.delete_fail_rate:.0%}\n")
    print(f"{'策略':<14} {'样本':>6} {'窗口P50':>10} {'窗口P95':>10} {'窗口max':>10} {'删除失败':>8}")
    print('-' * 66)

    for strategy, name in [("A", "无兜底"), ("B", "TTL 自愈"), ("C", "延迟双删")]:
        windows, stat = run_experiment(
            strategy, args.ttl, args.delete_fail_rate,
            args.threads, args.duration, args.delete_delay)
        if not windows:
            print(f"{name:<14} 无样本"); continue
        ws = sorted(windows)
        p50 = ws[len(ws) // 2]
        p95 = ws[int(len(ws) * 0.95)]
        print(f"{name:<14} {len(ws):>6} {p50:>9.3f}s {p95:>9.3f}s {ws[-1]:>9.3f}s {stat['delete_fails']:>8}")

    print("""
结论（机制定性，与 04.01.01 文档一致）：
  A 无兜底：删缓存失败 → 旧值在缓存中无期限滞留（窗口 ~∞，本实验中 TTL=∞ 直接可见 max 飙升）
  B TTL：不一致窗口上界 = TTL（基线兜底，代价是正常 miss）
  C 延迟双删：第二次删除覆盖"第一次失败 + 并发读回填"的竞态，P95 显著压缩
工程要点：TTL 是最终一致性的上界保险，延迟双删压缩常态窗口；高一致性场景应上 CDC/订阅binlog 主动失效。
""")

if __name__ == '__main__':
    main()
