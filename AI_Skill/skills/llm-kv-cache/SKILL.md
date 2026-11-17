---
name: llm-kv-cache
description: 大模型推理缓存（PagedAttention/RadixAttention/KV分层卸载/P-D分离/Mooncake/LMCache/KV驱逐策略）的机制与部署；用于推理平台缓存设计
---

# LLM 推理缓存架构（KV Cache）

> 覆盖 LLM 推理的 KV Cache 分页、前缀复用、分层卸载、P/D 分离与跨引擎生态，是 2024-2026 增长最快的缓存前沿。

## 1. 概述与适用场景

- **覆盖**：PagedAttention、RadixAttention、前缀缓存、分层卸载（HBM→CPU→SSD）、P-D 分离、Mooncake/LMCache/NIXL、KV 驱逐、MLA/量化。
- **适用**：推理平台架构设计；评审 04.03.15 文档；跟踪 vLLM/SGLang 生态。
- **不适用**：通用应用缓存（→ cache-architecture-patterns）；CPU/GPU 硬件细节（→ cpu-cache-architecture）。

## 2. 核心要点

1. 自回归生成的 KV Cache 显存占用 ≈ 2 × 层数 × 头数 × 头维 × 序列长度 × 精度字节；长上下文使显存成为首要瓶颈——这是本领域一切缓存优化的出发点（推导自 Transformer 注意力公式，项目 04.03.15 A 级）。
2. PagedAttention（vLLM，SOSP 2023）把 KV 按 block 分页管理，借鉴 OS 虚拟内存思想：内部碎片从连续分配的近 100% 降到 <4%，支持 prefix sharing 与 copy-on-write。
3. RadixAttention（SGLang，NeurIPS 2024）用基数树索引可复用前缀，LRU 驱逐叶节点，系统级复用率显著高于纯 vLLM 前缀缓存（实测值依赖负载，C 级）。
4. 前缀缓存收益：系统提示词/少样本缓存复用率在生产负载可达 60-90%（Mooncake 论文与项目 KV 模拟实验均支持，B/C 级）；本项目可运行模拟实测前缀复用率 85.5%（04.03.15 §实验）。
5. 分层卸载：HBM→CPU pinned memory→NVMe/对象存储；关键指标是换入换出的 TTFT 惩罚与命中率的权衡；vLLM 官方 KV Offloading Connector（2026-01）与 LMCache/TieringOffloadingSpec 提供 CPU+多级后端。
6. P/D 分离：Prefill（计算密集）与 Decode（访存密集）分池部署，KV 经高速链路（RDMA/NVLink/NIXL）传递；Mooncake（FAST 2025，ToS 2026）以 KVCache-centric 架构为 Kimi 生产验证；DistServe（ASPLOS'24）给出并行策略解耦分析。
7. 生态集成事实（2025-12 至 2026-05）：SGLang 上线 EPD（Encode-Prefill-Decode）三段解耦；Mooncake Transfer Engine 集成进 TensorRT-LLM（2025-12）与 vLLM v1 KV Connector；vLLM 官方 Mooncake Store 集成宣称 3.8× 吞吐、46× TTFT 降低（vllm.ai 2026-05-06，C 级厂商数据）。
8. KV 驱逐前沿：PrefixSim（libCacheSim，2026-11）支持 40+ 策略在真实 LLM trace 上对比"prefill 计算节省"，Apple 披露 RL 驱逐研究；LLM 前缀缓存的驱逐问题本质是"未来重用距离未知 + 前缀树结构约束"。

## 3. 权威速查

| 技术 | 出处 | 关键机制 | 状态（2026-11） |
| ---- | ---- | -------- | --------------- |
| PagedAttention | vLLM, SOSP 2023 | block 分页+COW | 事实标准 |
| RadixAttention | SGLang, NeurIPS 2024 | 基数树+LRU | 生产主流 |
| Mooncake | FAST 2025 | KV-centric 分离+RDMA | PyTorch 生态（2026-02） |
| LMCache | 开源 | 分层卸载+Blend | 与 vLLM 深度集成 |
| NIXL | NVIDIA | KV 传输抽象 | Dynamo/TRT-LLM 采用 |
| MLA | DeepSeek-V2 2024 | 低秩压缩 KV | 模型侧压缩主流方向 |
| PrefixSim | libCacheSim 2026-11 | 前缀缓存策略台架 | 评估新标准 |

## 4. 项目文档映射

| 知识点 | 项目文档 |
| ------ | -------- |
| 总览与机制 | [04.03.15](../../../docs/04-架构设计/04.03-行业应用场景/04.03.15-大模型推理缓存架构.md) |
| 分页/前缀实验 | 同上 §可运行实验（KV 模拟脚本） |
| 行业场景总览 | [04.03 README](../../../docs/04-架构设计/04.03-行业应用场景/README.md) |
| 算法对照（驱逐） | [01.02.10](../../../docs/01-理论基础/01.02-高级替换算法/01.02.10-S3-FIFO与SIEVE算法.md) |
| 新存储栈（分层） | [02.04.01](../../../docs/02-系统实现/02.04-现代内核缓存机制/02.04.01-新存储栈缓存技术.md) |
| 可观测性与 SLO | [04.03.18](../../../docs/04-架构设计/04.03-行业应用场景/04.03.18-LLM推理缓存的可观测性与SLO.md) |

## 5. 常见任务工作流

### 任务 A：推理平台缓存设计

1. 负载画像：系统提示占比、会话长度分布、多轮比例。
2. 第一层：引擎内前缀缓存（vLLM enable_prefix_caching / SGLang RadixAttention）。
3. 第二层：跨实例共享（Mooncake Store / LMCache）按 GPU 池划分。
4. 第三层：CPU/SSD 分层卸载按 TTFT SLO 设阈值。
5. 评估：用 PrefixSim 或内部 trace 回放对比策略。

### 任务 B：文档核对

核对 04.03.15 的论文出处与版本事实（vLLM/SGLang/Mooncake 时间点），更新以本技能 §6 为准并交叉核验官方博客。

## 6. 国际前沿对齐（截至 2026-11）

- 分层与压缩方向成型：**IMPRESS（FAST'25，重要性多层级前缀存储）**、**HACK（SIGCOMM'25，P/D 间 KV 压缩直算免反量化）**、**InstAttention（HPCA'25，KV 下沉计算存储设备）**——04.03.15 §8 分层判据的后续工作。
- 特征刻画与调度：**KVCache in the Wild（ATC'25，大规模云商 KV 复用特征）**为复用率基线提供真实数据参照；Preble（ICLR'25）分布式提示调度。
- 服务形态新进展：**ECHO（OSDI'26，稀疏注意力原生服务 + KV 卸载突破 HBM 限制）**、**LLM-42（SOSP'26，decode-verify-rollback 确定性推理）**——可观测性与正确性两个维度的新要求（04.03.18 的 burn_alert 与正确性类 SLO 可挂接）。
- vLLM v0.21.0 自动前缀缓存驱逐策略文档化（2026-07，04.03.18 §5 实操锚点）。
- libCacheSim PrefixSim（2026-11）支持 40+ 策略 LLM trace 对比（评估标准台架）。

## 7. 验证命令

```bash
python scripts/code_test_framework.py --test python   # 预期：0 失败（TC-DOC-001）
# 04.03.15 内 KV 模拟脚本：预期前缀复用率 ≈85.5%（TC-BENCH-002）
```

## 8. 权威参考

- **A 学术**：Kwon et al., "Efficient Memory Management for LLM Serving with PagedAttention", SOSP 2023；Zheng et al., "SGLang", NeurIPS 2024；Qin et al., "Mooncake", FAST 2025；Zhong et al., "DistServe", ASPLOS 2024；Sheng et al., "FlexGen", ICML 2023；Zhang et al., "H2O", ICLR 2024；DeepSeek-V2（MLA）, 2024
- **B 官方**：vLLM 博客（KV Offloading 2026-01-08；Mooncake Store 2026-05-06）；SGLang 文档；Mooncake 项目页（kvcache-ai.github.io/Mooncake）
- **C 工程**：libCacheSim PrefixSim（github.com/1a1a11a/libCacheSim）；GPUSmith 分层清单（2026-10）
