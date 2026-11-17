---
name: learning-driven-cache
description: 学习驱动缓存替换（LeCaR/CACHEUS/LRB/Hawkeye/3L-Cache/KV驱逐RL）的原理、训练与成本权衡；用于学习型方案评审与前沿跟踪
---

# 学习驱动缓存替换算法

> 覆盖机器学习辅助的缓存替换：从专家混合到强化学习，及学习增强的理论与工程代价。

## 1. 概述与适用场景

- **覆盖**：LeCaR、CACHEUS、LRB、Hawkeye、SHiP++、3L-Cache、Apple/RL KV 驱逐、学习增强竞争比。
- **适用**：评估"是否值得引入学习组件"；评审 01.04 文档；跟踪 ML×Systems 交叉前沿。
- **不适用**：常规选型（→ cache-algorithms-advanced，多数场景轻量算法已足够）；纯 LLM 推理缓存（→ llm-kv-cache）。

## 2. 核心要点

1. 谱系三代：①专家混合（LeCaR 用 LRU/LFU 两专家 + 逻辑回归仲裁，HotCloud 2018）；②逐对象分类（Hawkeye 用 learned oracle 预测"重用距离是否超容量"并映射到 eviction priority，ISCA 2016）；③RL/深度策略（LRB 把驱逐建模为 MDP，Song et al. 2020；3L-Cache FAST 2025 用轻量网络逼近 Belady）。
2. CACHEUS（FAST 2021）在 LeCaR 基础上引入 SR-LRU/CR-LFU 自适应专家与对抗稳健性，缓解对手 trace 退化。
3. 学习收益高度依赖 trace 平稳性；分布漂移时学习策略可能劣于 ARC/S3-FIFO——评审必须问"训练分布与服务负载是否同分布"。
4. 工程代价：推理延迟在命中路径上（ns-μs 级也致命）；常见做法是把模型移出关键路径（准入侧、后台重排、周期性策略切换）。
5. 理论前沿：学习增强在线算法（learned advice + 一致性竞争比保证）是 2022-2026 活跃方向，项目 01.04 已按 B/C 级登记。
6. KV Cache 驱逐 RL（Apple 2025 披露）证明学习型驱逐在 LLM 前缀缓存上有效，但特征工程与收益归因困难（C 级经验）。

## 3. 权威速查

| 算法 | 机制 | 模型开销 | 主要出处 |
| ---- | ---- | -------- | -------- |
| LeCaR | 两专家 + 权重学习 | 每命中 O(1) 更新 | HotCloud 2018 |
| Hawkeye | 分类器→优先级 | 训练离线、推理轻 | ISCA 2016 |
| LRB | RL（贝尔曼方程价值学习） | 推理在驱逐路径 | Song et al. 2020 |
| CACHEUS | 自适应双专家 | 同 LeCaR 量级 | FAST 2021 |
| 3L-Cache | 轻量 NN 学 Belady | 离线训练+在线推理 | FAST 2025 |

## 4. 项目文档映射

| 知识点 | 项目文档 |
| ------ | -------- |
| 总览与谱系 | [01.04 README](../../docs/01-理论基础/01.04-学习驱动缓存算法/README.md) |
| 对比与决策 | [01.05 算法对比与决策](../../docs/01-理论基础/01.05-算法对比与决策/README.md) |
| 基准方法 | [01.05.04](../../docs/01-理论基础/01.05-算法对比与决策/01.05.04-算法性能基准测试.md) |
| 非学习对照 | [01.02.10](../../docs/01-理论基础/01.02-高级替换算法/01.02.10-S3-FIFO与SIEVE算法.md) |

## 5. 常见任务工作流

### 任务 A：评审学习型提案

1. 收益证据：是否在与生产同分布的 trace 上对比了 ARC/S3-FIFO/SIEVE 强基线？
2. 延迟账：模型推理放在哪个路径？最坏情况增加多少 ns/ops？
3. 失效模式：分布漂移、对抗输入、冷启动分别如何处理？
4. 结论分级：A/B 级需论文出处；工程经验标 C 级并声明假设。

### 任务 B：季度前沿跟踪

检索 OSDI/SOSP/ATC/NSDI/MLSys + arXiv cs.LG×缓存，更新本技能 §6 与 01.04 README。

## 6. 国际前沿对齐（截至 2026-11）

- 3L-Cache（FAST 2025）确立"轻量网络逼近 Belady"范式，代码已开源（paraslab/3L-Cache）。
- libCacheSim 2026-11 PrefixSim 将驱逐策略对比（含学习策略）扩展到 LLM serving 前缀缓存，是评估"学习 vs 轻量"的新标准台架。
- LLM-Driven 启发式搜索（如 Vulcan, arXiv 2512.25065, 2026-04）用 LLM 生成逐实例驱逐启发式， Nine 个 SOTA 基线中含 3L-Cache/LeCaR/LRB/S3-FIFO/SIEVE——学习型与非学习型的混合范式出现。
- 理论侧：学习增强竞争比（Purohit et al., NeurIPS 2018 奠基）持续有新变体。

## 7. 验证命令

```bash
python scripts/benchmark/trace_benchmark.py   # 预期：基线命中率表，供学习方案对比（TC-BENCH-001）
python scripts/code_test_framework.py --test python   # 预期：0 失败（TC-DOC-001）
```

## 8. 权威参考

- **A 学术**：Vietri et al., HotCloud 2018（LeCaR）；Jain & Lin, ISCA 2016（Hawkeye）；Rodriguez et al., FAST 2021（CACHEUS）；Song et al., 2020（LRB, arXiv:2010.07814）；Zhou et al., FAST 2025（3L-Cache）；Purohit et al., NeurIPS 2018（learned advice）
- **B 官方**：3L-Cache 开源页；libCacheSim 文档
- **C 工程**：Apple ML KV 驱逐披露报道；Vulcan（arXiv:2512.25065）
