#!/usr/bin/env python3
"""
BufferCache 项目 —— Trace 驱动的缓存替换算法基准

功能：
1. 加载标准格式的访问 trace（CSV: timestamp,key,size,op）
2. 内置合成 trace 生成器（Zipf 主分布 + 扫描突发，逼近生产负载特征）
3. 对 LRU / LFU / S3-FIFO(简化) 跑同一 trace，输出 miss ratio 对比
4. 支持接入公开数据集（见文件末尾"公开 Trace 来源"）

用法：
    python scripts/benchmark/trace_benchmark.py                     # 合成 trace 基准
    python scripts/benchmark/trace_benchmark.py --trace file.csv    # 自有 CSV trace
    python scripts/benchmark/trace_benchmark.py --capacity 5000 --ops 200000

对应文档: docs/01-理论基础/01.05-算法对比与决策/01.05.04-算法性能基准测试.md
"""

import argparse
import csv
import heapq
import random
from collections import OrderedDict, Counter

# ---------------------------------------------------------------------------
# 合成 trace 生成器
# ---------------------------------------------------------------------------

def synth_trace(num_ops: int, num_keys: int, zipf_s: float = 1.0,
                scan_ops_ratio: float = 0.05, scan_len: int = 100, seed: int = 42):
    """生成合成访问序列。

    主分布为 Zipf（参数 zipf_s，生产缓存负载的经验范围 0.8-1.2）；
    scan_ops_ratio 控制扫描操作占总操作的比例（模拟备份/批处理对缓存的污染），
    扫描段为长度 scan_len 的顺序新键段，均匀散布在序列中。
    """
    rng = random.Random(seed)
    weights = [1.0 / (i + 1) ** zipf_s for i in range(num_keys)]
    total = sum(weights)
    cum, acc = [], 0.0
    for w in weights:
        acc += w / total
        cum.append(acc)

    def zipf_key():
        r = rng.random()
        lo, hi = 0, len(cum) - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if cum[mid] < r:
                lo = mid + 1
            else:
                hi = mid
        return f"k{lo}"

    keys = [f"s{i}" for i in range(num_keys)]
    scan_period = max(scan_len, int(scan_len / scan_ops_ratio)) if scan_ops_ratio > 0 else num_ops + 1
    next_scan_at = rng.randrange(scan_period)
    i = 0
    while i < num_ops:
        if i >= next_scan_at and scan_ops_ratio > 0:
            base = rng.randrange(max(1, num_keys - scan_len))
            for j in range(scan_len):
                if i + j >= num_ops:
                    break
                yield keys[(base + j) % num_keys]
            i += scan_len
            next_scan_at = i + rng.randrange(scan_period)
        else:
            yield zipf_key()
            i += 1

# ---------------------------------------------------------------------------
# 算法实现
# ---------------------------------------------------------------------------

class LRUCache:
    """O(1) LRU：哈希表 + 双向链表（OrderedDict）"""
    def __init__(self, capacity: int):
        self.cap = capacity
        self.data = OrderedDict()

    def access(self, key) -> bool:
        if key in self.data:
            self.data.move_to_end(key)
            return True
        if len(self.data) >= self.cap:
            self.data.popitem(last=False)
        self.data[key] = None
        return False

class LFUCache:
    """简化 LFU：频率计数 + 最小堆（tie-break 用插入序号）"""
    def __init__(self, capacity: int):
        self.cap = capacity
        self.freq = {}
        self.heap = []
        self.tick = 0

    def access(self, key) -> bool:
        self.tick += 1
        if key in self.freq:
            self.freq[key] += 1
            heapq.heappush(self.heap, (self.freq[key], self.tick, key))
            return True
        if len(self.freq) >= self.cap:
            while self.heap:
                f, _, k = heapq.heappop(self.heap)
                if self.freq.get(k) == f:
                    del self.freq[k]
                    break
        self.freq[key] = 1
        heapq.heappush(self.heap, (1, self.tick, key))
        return False

class S3FIFOCache:
    """S3-FIFO 简化实现：S(10%) + M(90%) + 2bit 计数器

    对应 docs/01-理论基础/01.02-高级替换算法/01.02.10-S3-FIFO与SIEVE算法.md
    幽灵队列 G 在本基准中省略（不影响 miss ratio 对比的主结论）。
    """
    def __init__(self, capacity: int):
        self.s_cap = max(1, capacity // 10)
        self.m_cap = capacity - self.s_cap
        self.S = OrderedDict()   # key -> freq(0-3)
        self.M = OrderedDict()   # key -> freq(0-3)

    def access(self, key) -> bool:
        if key in self.S:
            self.S[key] = min(3, self.S[key] + 1)
            return True
        if key in self.M:
            self.M[key] = min(3, self.M[key] + 1)
            return True
        # miss：入 S
        if len(self.S) >= self.s_cap:
            old, f = self.S.popitem(last=False)
            if f > 0:
                # 晋升 M；M 满则驱逐（freq<3 者驱逐，=3 者 second chance）
                if len(self.M) >= self.m_cap:
                    while True:
                        old_m, f_m = next(iter(self.M.items()))
                        del self.M[old_m]
                        if f_m < 3:
                            break
                        self.M[old_m] = f_m - 1
                self.M[old] = f
            # f == 0 的对象直接淘汰（生产实现中进入幽灵队列 G）
        self.S[key] = 0
        return False

ALGORITHMS = {"LRU": LRUCache, "LFU": LFUCache, "S3-FIFO": S3FIFOCache}

# ---------------------------------------------------------------------------
# 基准执行
# ---------------------------------------------------------------------------

def run(trace_gen, capacity: int, ops: int):
    caches = {name: cls(capacity) for name, cls in ALGORITHMS.items()}
    misses = Counter()
    total = 0
    for key in trace_gen:
        if total >= ops:
            break
        total += 1
        for name, c in caches.items():
            if not c.access(key):
                misses[name] += 1
    return total, misses

def load_csv_trace(path: str):
    """加载 CSV trace：timestamp,key,size,op（size/op 列可选）"""
    def gen():
        with open(path, newline='', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                yield row['key']
    return gen()

def main():
    ap = argparse.ArgumentParser(description='缓存算法 trace 基准')
    ap.add_argument('--trace', help='CSV trace 文件路径（含 key 列）')
    ap.add_argument('--capacity', type=int, default=1000)
    ap.add_argument('--ops', type=int, default=200000)
    ap.add_argument('--keys', type=int, default=2500, help='合成 trace 键空间')
    ap.add_argument('--zipf', type=float, default=0.9, help='Zipf 参数')
    ap.add_argument('--scan', type=float, default=0.05, help='扫描操作占比（0-1）')
    args = ap.parse_args()

    if args.trace:
        trace = load_csv_trace(args.trace)
    else:
        trace = synth_trace(args.ops, args.keys, args.zipf, args.scan)

    total, misses = run(trace, args.capacity, args.ops)
    print(f"{'算法':<10} {'miss数':>10} {'miss ratio':>12}")
    print('-' * 34)
    for name in ALGORITHMS:
        mr = misses[name] / total
        print(f"{name:<10} {misses[name]:>10} {mr:>11.2%}")
    print(f"\ntotal ops: {total}, capacity: {args.capacity}")
    print("参考结论（合成 trace）：扫描占比升高时，S3-FIFO 相对 LRU 的 miss ratio 优势扩大（对齐 SOSP'23 论文定性结论）")

if __name__ == '__main__':
    main()

# ---------------------------------------------------------------------------
# 公开 Trace 来源（接入时把下载文件转为含 key 列的 CSV 即可用 --trace 运行）
# ---------------------------------------------------------------------------
# 1. MSR Cambridge Block Traces（块级，SNIA IOTTA 托管）:
#    https://iotta.snia.org/tracetypes/3 （MSR 2007/2016 系列，多用于缓存/存储论文）
# 2. Twitter Cache Cluster Traces（2019-2020，memcache 生产负载）:
#    随 "Twemcache / Cache clusters at Twitter" 研究发布（Yang & Rashmi, OSDI 2020 使用）
# 3. Wiki / CDN 内容请求 trace: CAIDA、The Massachusetts Wiki 数据集
# 4. 转换示例: MSR trace 的 (timestamp, disk_id, block_id, size, op) 可将 block_id
#    按 (disk_id, block_id) 组合为 key 列
