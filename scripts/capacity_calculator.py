#!/usr/bin/env python3
"""
BufferCache 项目 —— 缓存容量与成本估算器（公式可执行化）

把 05.06（性能优化公式）与 07.05.04（集群容量规划）的纸面公式固化为工具：
输入负载参数，输出内存需求、实例/分片配置、网络带宽与月成本估算。

参数经验值均为 C 级（项目经验模型，见 docs/00-项目总览/公式-文献对照表），
云上单价为 2026-11 公开刊例的量级参考，输出结果仅供容量评审起点，
生产值必须压测校准（本工具不替代 TC-CLUS 系列实测）。

用法：
    python scripts/capacity_calculator.py --qps 50000 --avg-value 2048 --keys 20000000
    python scripts/capacity_calculator.py --interactive

输出：文本报告（--json 输出结构化数据）。
"""

import argparse
import json
import math

# C 级经验参数（声明假设，可 --override）
PER_KEY_OVERHEAD = 100      # 元数据/指针/SDS 头 每 key 字节（dictEntry+robj+SDS，经验值）
FRAG_FACTOR = 1.25          # 内存碎片与复制 backlog 余量
SAFE_UTIL = 0.70            # 单实例 maxmemory / 物理内存（留 fork COW 与系统余量）
INSTANCE_GB = [8, 16, 32, 64]            # 候选实例档位
QPS_PER_CORE = 80_000                    # 单核吞吐经验值（事件循环，pipeline 深度相关）
CORES_PER_8G = 2                         # 8GB 档 vCPU 配比对标

CLOUD_PRICE_PER_GB_MONTH = 3.5           # 云上 Valkey 托管量级价（C 级 2026-11 参考）
BANDWIDTH_UNIT = 1e9                     # Gbps 换算


def calc(args, qps_per_core=QPS_PER_CORE):
    peak_qps = args.qps * args.peak
    # 1. 数据内存：keys × (value + 开销) × 碎片系数
    per_key = args.avg_value + PER_KEY_OVERHEAD
    data_bytes = args.keys * per_key * FRAG_FACTOR
    # 2. 副本总量（主+从）
    total_bytes = data_bytes * (1 + args.replicas)
    # 3. 实例分档：满足 SAFE_UTIL 的最小档位
    need_gb = total_bytes / 1e9
    inst = next((g for g in INSTANCE_GB if g * SAFE_UTIL >= need_gb / max(1, math.ceil(need_gb / (INSTANCE_GB[-1] * SAFE_UTIL)))), INSTANCE_GB[-1])
    n_shards = max(1, math.ceil(need_gb / (inst * SAFE_UTIL)))
    n_instances = n_shards * (1 + args.replicas)
    # 4. CPU 维度校验：QPS 所需核数 → 反推实例数下限
    cores_needed = peak_qps / qps_per_core
    cores_per_inst = max(2, int(inst / 8) * CORES_PER_8G)
    n_by_cpu = math.ceil(cores_needed / cores_per_inst)
    n_instances = max(n_instances, n_by_cpu * (1 + args.replicas))
    # 5. 带宽：读占比 × QPS × value + 复制/管理余量 20%
    read_qps = peak_qps * args.read_ratio
    bw_bps = read_qps * args.avg_value * 8 * 1.2
    # 6. 成本（主+从全价）
    cost_month = n_instances * inst * CLOUD_PRICE_PER_GB_MONTH
    return dict(
        peak_qps=int(peak_qps),
        data_memory_gb=round(data_bytes / 1e9, 1),
        total_memory_with_replicas_gb=round(total_bytes / 1e9, 1),
        instance_gb=inst,
        shards=n_shards,
        replicas=args.replicas,
        instances=n_instances,
        bandwidth_gbps=round(bw_bps / BANDWIDTH_UNIT, 2),
        cores_needed=round(cores_needed, 1),
        cost_month_usd=round(cost_month),
        assumptions=dict(per_key_overhead=PER_KEY_OVERHEAD, frag=FRAG_FACTOR,
                         safe_util=SAFE_UTIL, qps_per_core=qps_per_core,
                         price_gb_month=CLOUD_PRICE_PER_GB_MONTH),
    )


def report(r):
    a = r["assumptions"]
    print("=" * 60)
    print("缓存容量与成本估算报告（C 级经验模型，压测校准后生效）")
    print("=" * 60)
    print(f"峰值 QPS              {r['peak_qps']:>12,}")
    print(f"数据内存（含碎片）    {r['data_memory_gb']:>10} GB")
    print(f"含副本总内存          {r['total_memory_with_replicas_gb']:>10} GB")
    print(f"建议实例档位          {r['instance_gb']:>10} GB")
    print(f"主分片数              {r['shards']:>10}")
    print(f"副本数/主             {r['replicas']:>10}")
    print(f"总实例数              {r['instances']:>10}")
    print(f"读带宽需求            {r['bandwidth_gbps']:>10} Gbps")
    print(f"CPU 核数需求          {r['cores_needed']:>10}")
    print(f"月成本估算            {r['cost_month_usd']:>10} USD")
    print("-" * 60)
    print(f"假设: 元数据/key={a['per_key_overhead']}B  碎片系数={a['frag']}  "
          f"安全水位={a['safe_util']:.0%}  单核={a['qps_per_core']:,}QPS  "
          f"单价=${a['price_gb_month']}/GB/月")
    print("校准: 跑 redis-benchmark（redis-lab）实测单实例吞吐后，用 --qps-per-core 覆盖默认值")


def main():
    ap = argparse.ArgumentParser(description="缓存容量与成本估算器")
    ap.add_argument('--qps', type=int, default=50_000, help='平均 QPS（峰值另乘系数）')
    ap.add_argument('--avg-value', type=int, default=2048, help='平均 value 字节')
    ap.add_argument('--keys', type=int, default=20_000_000, help='key 总数')
    ap.add_argument('--read-ratio', type=float, default=0.9, help='读操作占比 0-1')
    ap.add_argument('--peak', type=float, default=3.0, help='峰值系数（大促 3-10）')
    ap.add_argument('--replicas', type=int, default=1, help='每主副本数')
    ap.add_argument('--qps-per-core', type=int, default=QPS_PER_CORE, help='校准值')
    ap.add_argument('--json', action='store_true', help='结构化输出')
    args = ap.parse_args()

    r = calc(args, qps_per_core=args.qps_per_core)
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        report(r)


if __name__ == '__main__':
    main()
