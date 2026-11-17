---
name: cache-security
description: 缓存安全（CPU侧信道/Spectre-Meltdown/TLB/CacheWarp/Web缓存投毒/CPDoS/CI缓存投毒）与防护体系；用于安全评审与加固方案
---

# 缓存安全

> 覆盖硬件缓存侧信道到 Web 缓存攻击的全谱系与防护体系，是缓存系统的安全评审基线。

## 1. 概述与适用场景

- **覆盖**：Flush+Reload/Prime+Probe、Spectre/Meltdown、TLB 侧信道、CacheWarp、Web 缓存投毒、CPDoS、DNS 缓存投毒、CI 缓存投毒、CAT/常数时间防护。
- **适用**：安全评审；加固方案设计；评审 04.02 文档。
- **不适用**：通用 Web 安全（OWASP 全集）；应用业务逻辑安全。

## 2. 核心要点

1. 共享微架构状态是侧信道的物理基础：L1/L2 按核私有（超线程共享 L1），LLC 跨核共享——同机多租户/超线程共置是主要威胁模型；Prime+Probe 不需共享内存，Flush+Reload 需共享页（Dedup/KSM 助纣）。
2. Spectre（边界检查绕过，2018）/Meltdown（内核页隔离失效，2018）通过瞬态执行把缓存变为泄露通道；缓解（retpoline、KPTI、微码）带来 1-30% 性能代价（范围取决于负载，C 级）。
3. CacheWarp（USENIX Security 2023）：对 AMD SEV 加密虚拟机注入历史版本缓存行，破坏完整性（非机密性）；修复涉及 VMPL 权限收紧与 hypervisor 行为变更。
4. Web 缓存投毒：污染 CDN/反向代理缓存使恶意响应分发给其他用户；现代变体利用未键化头（X-Forwarded-Host 等）与 Fat GET；CPDoS（USENIX Security 2020）用"缓存键扩大 + 错误响应缓存"实现拒绝服务。
5. CI 缓存投毒：构建缓存（依赖层、编译缓存）被注入恶意产物→供应链污染；防护：缓存命名空间按签名隔离、不可变 key、来源证明（SLSA/in-toto）。
6. 防护体系分层：架构层（禁超线程/核隔离、CAT/MBA 分区）、密码层（常数时间实现、屏蔽实现）、系统层（页着色、KSM 关闭、缓存清理上下文切换）、应用层（缓存键规范化、响应头白名单）。
7. 检测：性能计数器异常（cache-miss 突增）、Prime+Probe 的 LLC 冲突模式检测（cache-mon 类研究原型），工程成熟度低（C 级）。

## 3. 权威速查

| 攻击 | 目标层 | 前提 | 代表出处 |
| ---- | ------ | ---- | -------- |
| Flush+Reload | LLC | 共享内存页 | Yarom & Falkner, USENIX Sec 2014 |
| Prime+Probe | LLC | 共置（无需共享） | Osvik et al., CHES 2006 谱系 |
| Spectre/Meltdown | 瞬态执行 | 本地代码执行 | IEEE S&P / USENIX Sec 2018 |
| CacheWarp | SEV 完整性 | SEV VM | USENIX Sec 2023 |
| Web 缓存投毒 | CDN/代理 | 键配置错误 | PortSwigger 研究 2018-2020 |
| CPDoS | 缓存 DoS | 错误响应可缓存 | USENIX Sec 2020 |
| CI 缓存投毒 | 构建缓存 | 共享缓存命名空间 | CISA/社区披露 2023+ |

## 4. 项目文档映射

| 知识点 | 项目文档 |
| ------ | -------- |
| 总览 | [04.02 README](../../../docs/04-架构设计/04.02-缓存安全/README.md) |
| CPU 侧信道 | 同上（Flush+Reload/Prime+Probe 节） |
| Web 层攻击 | 同上（投毒/CPDoS 节） |
| 防护体系 | 同上（CAT/常数时间/分层防护节） |
| 侧信道与缓存索引 | [02.02 README 关联](../../../docs/02-系统实现/02.02-CPU缓存架构/) |

## 5. 常见任务工作流

### 任务 A：多租户缓存服务安全评审

1. 威胁模型：同机敌手是否存在（容器密度、超线程开启状态）。
2. 架构层：核/LLC 分区（CAT）、禁 SMT 的选项成本。
3. 密码层：密钥操作是否常数时间；是否隔离到专用核。
4. 输出：风险清单 + 缓解代价评估。

### 任务 B：Web 缓存配置审计

1. 列出全部缓存键（Vary、query、header）。
2. 检查未键化输入是否影响响应体；错误响应是否可缓存（Cache-Control on 4xx/5xx）。
3. 用 Param Miner/Burp 做投毒回归测试。

## 6. 国际前沿对齐（截至 2026-11）

- 侧信道检测与缓存分区（Intel CAT/MBA、AMD QoS）持续演进；学术界关注"缓存索引随机化"与 LLC 非包含化（non-inclusive）带来的新攻击面。
- SEV-SNP/TDX 机密计算普及推动完整性攻击（CacheWarp 类）研究升温。
- CI 供应链安全标准化：SLSA provenance 与缓存隔离成为企业 CI 默认要求。

## 7. 验证命令

```bash
python scripts/code_test_framework.py --test python   # 预期：0 失败（TC-DOC-001）
# 人工：lscpu 检查超线程与缓存拓扑；curl 缓存键探测（TC-SEC-001）
```

## 8. 权威参考

- **A 学术**：Yarom & Falkner, USENIX Security 2014；Lipp et al., USENIX Security 2018（Meltdown）；Kocher et al., IEEE S&P 2019（Spectre）；Wilke et al., USENIX Security 2023（CacheWarp）；Hoai et al., USENIX Security 2020（CPDoS）；Osvik et al., CHES 2006（Prime+Probe 谱系）
- **B 官方**：Intel CAT 文档；AMD SEV 白皮书；PortSwigger Web Cache Poisoning 研究；CISA CI 供应链指南
- **C 工程**：cachemon 检测原型；Linux kernel mitigations 文档（/sys/devices/system/cpu/vulnerabilities/）
