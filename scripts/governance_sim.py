#!/usr/bin/env python3
"""
缓存治理策略模拟器（TC-BENCH-006）

把 04.44 的三大治理问题（穿透/雪崩/击穿）从文字方案变成可执行对比：
注入攻击/故障场景，对比"无防护 vs 标准防护"的 DB 回源压力。

场景与防护映射（对应 docs/04-架构设计/04.04-缓存问题与治理/）：
  penetrate  缓存穿透：不存在 key 的风暴查询
             无防护=全穿透打 DB；防护=布隆过滤器 + 空值缓存(TTL 5s)
  avalanche  缓存雪崩：60% 的 key 同一时刻批量过期
             无防护=回源洪峰；防护=TTL 抖动(±20%)
  breakdown  缓存击穿：热点 key 过期瞬间 200 并发重建
             无防护=200 路并发回源；防护=互斥重建(单飞, 其余等 30ms 重查)

用法：
    python scripts/governance_sim.py                # 三场景全跑
    python scripts/governance_sim.py --scene breakdown --requests 2000

输出：DB 回源次数 / 有效服务请求 / 回源放大比，防护收益自动对比。
"""

import argparse
import random
import threading
import time
from collections import OrderedDict

DB_LATENCY_MS = 20          # 模拟 DB 回源耗时（C 级经验值，影响击穿场景并发窗口）


class Cache:
    def __init__(self, capacity=500):
        self.data = OrderedDict()
        self.cap = capacity
        self.lock = threading.Lock()

    def get(self, k, now):
        with self.lock:
            if k in self.data:
                v, exp = self.data[k]
                if exp is None or exp > now:
                    self.data.move_to_end(k)
                    return v
                del self.data[k]
        return None

    def set(self, k, v, ttl=None, now=0.0):
        with self.lock:
            if len(self.data) >= self.cap:
                self.data.popitem(last=False)
            self.data[k] = (v, (now + ttl) if ttl else None)


class BloomFilter:
    """极简位图布隆（演示精度足够）"""

    def __init__(self, size=8192, hashes=3):
        self.bits = bytearray(size // 8)
        self.size = size
        self.hashes = hashes

    def _h(self, k, i):
        return hash((k, i)) % self.size

    def add(self, k):
        for i in range(self.hashes):
            self.bits[self._h(k, i) // 8] |= 1 << (self._h(k, i) % 8)

    def __contains__(self, k):
        return all(self.bits[self._h(k, i) // 8] >> (self._h(k, i) % 8) & 1 for i in range(self.hashes))


class Sim:
    def __init__(self):
        self.db_hits = 0          # 实际打到 DB 的回源次数
        self.db_lock = threading.Lock()
        self.db_times = []        # 回源时间戳（峰值统计）
        self.db_sem = threading.Semaphore(10**6)   # 无防护时近似无限并发
        self.cache = Cache()

    def db_get(self, key):
        with self.db_lock:
            self.db_hits += 1
            self.db_times.append(time.time())
        time.sleep(DB_LATENCY_MS / 1000)
        return f"v_{key}"

    def peak_rate(self, window=0.01):
        """每 window 秒桶的回源数最大值（近似瞬时洪峰）。"""
        if not self.db_times:
            return 0
        ts = sorted(self.db_times)
        best = cur = 1
        j = 0
        for i in range(1, len(ts)):
            while ts[i] - ts[j] > window:
                j += 1
            cur = i - j + 1
            best = max(best, cur)
        return best


# ---------- 场景 1：穿透 ----------

def scene_penetrate(sim, requests, protect, seed):
    rng = random.Random(seed)
    bloom = BloomFilter()
    for i in range(400):          # 预置存在的 key
        bloom.add(f"key_{i}")
        sim.cache.set(f"key_{i}", f"v_{i}", now=time.time())
    valid = [f"key_{i}" for i in range(400)]
    db_count_start = sim.db_hits
    for _ in range(requests):
        if rng.random() < 0.5:
            k = rng.choice(valid)                  # 存在的 key
        else:
            k = f"nope_{rng.randrange(10**6)}"     # 必然不存在
        now = time.time()
        v = sim.cache.get(k, now)
        if v is None:
            if protect and k not in bloom:         # 布隆判定不存在 → 空值缓存挡 DB
                sim.cache.set(k, "NULL", ttl=5, now=now)
                continue
            v = sim.db_get(k)
            sim.cache.set(k, v, now=now)
    return sim.db_hits - db_count_start


# ---------- 场景 2：雪崩 ----------

def scene_avalanche(sim, requests, protect, seed):
    rng = random.Random(seed)
    now = time.time()
    keys = [f"av_{i}" for i in range(500)]
    for k in keys[:300]:                             # 60% 的 key 同一时刻过期
        ttl = 0.05
        if protect:
            ttl *= rng.uniform(0.6, 1.4)             # TTL 抖动把过期时刻打散
        sim.cache.set(k, f"v_{k}", ttl=ttl, now=now)
    for k in keys[300:]:
        sim.cache.set(k, f"v_{k}", ttl=100, now=now)
    # 请求期横跨抖动窗口：无防护组此时已全部同刻过期，防护组过期被时间摊开
    time.sleep(0.045 if protect else 0.06)
    db_count_start = sim.db_hits
    for i in range(requests):
        k = rng.choice(keys)
        now = time.time()
        v = sim.cache.get(k, now)
        if v is None:
            v = sim.db_get(k)
            sim.cache.set(k, v, ttl=100, now=now)
    return sim.db_hits - db_count_start


# ---------- 场景 3：击穿（互斥重建） ----------

def scene_breakdown(sim, requests, protect, seed, concurrency=200):
    hot_key = "hot:item"
    rng = random.Random(seed)
    served = [0]
    db_start = sim.db_hits

    def worker():
        for _ in range(requests // concurrency):
            now = time.time()
            v = sim.cache.get(hot_key, now)
            if v is None:
                if protect:
                    # 单飞：抢锁者回源，其余短等重查
                    if getattr(sim, "_hot_lock", None) is None:
                        sim._hot_lock = threading.Lock()
                    if not sim._hot_lock.acquire(blocking=False):
                        time.sleep(0.03)
                        v = sim.cache.get(hot_key, time.time())
                        if v is not None:
                            served[0] += 1
                            continue
                        # 等后仍无（抢锁者慢）→ 回源兜底
                    else:
                        try:
                            v = sim.db_get(hot_key)
                            sim.cache.set(hot_key, v, ttl=60, now=time.time())
                            served[0] += 1
                            continue
                        finally:
                            sim._hot_lock.release()
                v = sim.db_get(hot_key)
                sim.cache.set(hot_key, v, ttl=60, now=time.time())
            served[0] += 1

    sim.cache.data.clear()                            # 热点未过期前被清 → 模拟过期瞬间
    threads = [threading.Thread(target=worker) for _ in range(concurrency)]
    for t in threads: t.start()
    for t in threads: t.join()
    return sim.db_hits - db_start, served[0]


def main():
    ap = argparse.ArgumentParser(description="缓存治理策略模拟器")
    ap.add_argument("--scene", choices=["penetrate", "avalanche", "breakdown"], default=None)
    ap.add_argument("--requests", type=int, default=3000)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    scenes = [args.scene] if args.scene else ["penetrate", "avalanche", "breakdown"]
    print(f"{'场景':<12} {'防护':<6} {'DB回源':>8} {'放大比':>10}")
    print('-' * 42)

    for scene in scenes:
        sim = Sim()
        if scene == "breakdown":
            db_raw, _ = scene_breakdown(sim, args.requests, False, args.seed)
            sim2 = Sim()
            db_prot, served = scene_breakdown(sim2, args.requests, True, args.seed)
            peak_raw, peak_prot = sim.peak_rate(), sim2.peak_rate()
        else:
            fn = {"penetrate": scene_penetrate, "avalanche": scene_avalanche}[scene]
            db_raw = fn(sim, args.requests, False, args.seed)
            sim2 = Sim()
            db_prot = fn(sim2, args.requests, True, args.seed)
            served = args.requests
            peak_raw, peak_prot = sim.peak_rate(), sim2.peak_rate()
        amp_raw = db_raw / max(served, 1)
        amp_prot = db_prot / max(served, 1)
        print(f"{scene:<12} {'无':<6} {db_raw:>8} {amp_raw:>9.2f}x  峰值{peak_raw:>4}/10ms")
        print(f"{scene:<12} {'有':<6} {db_prot:>8} {amp_prot:>9.2f}x  峰值{peak_prot:>4}/10ms")
        gain = (1 - db_prot / max(db_raw, 1)) * 100
        pgain = (1 - peak_prot / max(peak_raw, 1)) * 100
        print(f"{'':<12} 防护收益: 回源总量 -{gain:.0f}% / 回源峰值 -{pgain:.0f}%\n")


if __name__ == "__main__":
    main()
