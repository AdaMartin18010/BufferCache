#!/usr/bin/env python3
"""
KV 缓存驱逐策略对比实验（TC-BENCH-007，04.03.15 实验节升级）

在 LLM 风格负载（共享系统前缀 + 会话分支）下对比三种块驱逐策略：
  LRU    经典最近最少使用（OrderedDict）
  FIFO   S3-FIFO 简化版（S 段准入 + M 段）
  SIEVE  单队列 + visited 位 + 驱逐指针

负载模型：模拟多轮对话——系统前缀 200 token 共享，每会话带独立历史；
会话数超块池容量时产生驱逐压力（复用率可经 --sessions 调节）。

用法：
    python scripts/kv_evict_bench.py                 # 默认三策略
    python scripts/kv_evict_bench.py --sessions 80 --blocks 64

输出：各策略 token 复用率（命中 token / 总 token）与 prefill 节省估算。
对应文档: docs/04-架构设计/04.03-行业应用场景/04.03.15 §8.5
"""

import argparse
import random
from collections import OrderedDict


class KVPoolLRU:
    def __init__(self, num_blocks, block_size=16):
        self.cap = num_blocks
        self.bs = block_size
        self.cache = OrderedDict()     # block_hash -> None

    def request(self, tokens):
        hit_tokens = 0
        prev = 0
        for i in range(0, len(tokens), self.bs):
            chunk = tuple(tokens[i:i + self.bs])
            h = hash((chunk, prev))
            if h in self.cache:
                self.cache.move_to_end(h)
                hit_tokens += len(chunk)
            else:
                if len(self.cache) >= self.cap:
                    self.cache.popitem(last=False)
                self.cache[h] = None
            prev = h
        return hit_tokens


class KVPoolFIFO:
    """S3-FIFO 简化：S(准入,比例可调) + M(其余)，freq>0 晋升，幽灵队列省略。"""

    def __init__(self, num_blocks, block_size=16, s_ratio=0.1):
        self.bs = block_size
        self.s_cap = max(1, int(num_blocks * s_ratio))
        self.m_cap = num_blocks - self.s_cap
        self.S = OrderedDict()   # h -> freq
        self.M = OrderedDict()   # h -> freq
        self.s_ratio = s_ratio

    def request(self, tokens):
        hit_tokens = 0
        prev = 0
        for i in range(0, len(tokens), self.bs):
            chunk = tuple(tokens[i:i + self.bs])
            h = hash((chunk, prev))
            if h in self.S:
                self.S[h] = min(3, self.S[h] + 1)
                hit_tokens += len(chunk)
            elif h in self.M:
                self.M[h] = min(3, self.M[h] + 1)
                hit_tokens += len(chunk)
            else:
                if len(self.S) >= self.s_cap:
                    old, f = self.S.popitem(last=False)
                    if f > 0:
                        while len(self.M) >= self.m_cap:
                            om, fm = next(iter(self.M.items()))
                            del self.M[om]
                            if fm < 3:
                                break
                            self.M[om] = fm - 1
                        self.M[old] = f
                self.S[h] = 0
            prev = h
        return hit_tokens


class KVPoolSIEVE:
    """单 FIFO 队列 + visited 位；命中置位；驱逐从队首扫第一个未访问者。"""

    def __init__(self, num_blocks, block_size=16):
        self.cap = num_blocks
        self.bs = block_size
        self.q = OrderedDict()     # h -> visited
        self.hand = None           # 驱逐扫描指针（用迭代位置模拟：队首扫描）

    def request(self, tokens):
        hit_tokens = 0
        prev = 0
        for i in range(0, len(tokens), self.bs):
            chunk = tuple(tokens[i:i + self.bs])
            h = hash((chunk, prev))
            if h in self.q:
                self.q[h] = True
                hit_tokens += len(chunk)
            else:
                if len(self.q) >= self.cap:
                    # 队首扫描：找到并删除第一个未访问块
                    for cand in list(self.q.keys()):
                        if not self.q[cand]:
                            del self.q[cand]
                            break
                    else:
                        self.q.popitem(last=False)   # 全被访问过 → 淘汰最旧
                self.q[h] = False
            prev = h
        return hit_tokens


def gen_workload(num_sessions, seed=7):
    """LLM 多轮对话负载：共享系统前缀 + 会话内历史累积。"""
    rng = random.Random(seed)
    system = list(range(200))                 # 共享前缀
    sessions = []
    for s in range(num_sessions):
        hist = system + [1000 + s * 100 + i for i in range(rng.randint(5, 25))]
        for turn in range(rng.randint(1, 4)):
            hist = hist + [2000 + turn * 10 + rng.randrange(5) for _ in range(rng.randint(3, 15))]
        sessions.append(hist)
    return sessions


def main():
    ap = argparse.ArgumentParser(description="KV 驱逐策略对比")
    ap.add_argument("--blocks", type=int, default=64, help="KV 块池容量")
    ap.add_argument("--sessions", type=int, default=60, help="会话数（>容量产生驱逐压力）")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--s-ratio", type=float, default=0.1, help="S3-FIFO 的 S 段占比（敏感性实验）")
    args = ap.parse_args()

    workloads = gen_workload(args.sessions, args.seed)
    total_tokens = sum(len(w) for w in workloads)

    print(f"负载: {args.sessions} 会话, 块池 {args.blocks} blocks(16 token/block), 总 token {total_tokens}")
    print(f"{'策略':<16} {'命中token':>10} {'复用率':>8} {'prefill节省':>10}")
    print('-' * 52)
    for name, cls in [("LRU", KVPoolLRU), (f"FIFO(S3,s={args.s_ratio:.0%})", KVPoolFIFO), ("SIEVE", KVPoolSIEVE)]:
        pool = cls(args.blocks, s_ratio=args.s_ratio) if cls is KVPoolFIFO else cls(args.blocks)
        hit = sum(pool.request(w) for w in workloads)
        r = hit / total_tokens
        print(f"{name:<16} {hit:>10} {r:>8.1%} {r:>9.1%}")
    if args.s_ratio * args.blocks * 16 < 200:
        print("\n⚠ 提示: S 段容量(S比例×池)小于共享前缀(200 token)时，S3-FIFO 会把前缀挤出 → 复用率塌缩")
        print("  （--s-ratio 0.3 复跑可见恢复；前缀型负载对准入段容量敏感，这是 FIFO 系的固有特性）")
    print("\n注：prefill 节省≈复用率（忽略末块部分命中与调度开销）。")


if __name__ == "__main__":
    main()
