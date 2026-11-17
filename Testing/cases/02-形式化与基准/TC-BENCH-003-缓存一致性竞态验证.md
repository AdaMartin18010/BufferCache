# TC-BENCH-003 缓存一致性竞态验证

- **用例ID**：TC-BENCH-003 | **优先级**：P2 | **自动化**：self_verify 已覆盖（`consistency` 子命令）
- **目的**：可执行验证 Cache-Aside 写路径在并发+删缓存失败下的不一致窗口，量化 TTL/延迟双删策略效果（04.01.01 文档结论的执行证据）
- **关联**：[scripts/consistency_check.py](../../../scripts/consistency_check.py)；[04.01.01 Cache-Aside](../../../docs/04-架构设计/04.01-缓存架构模式/04.01.01-Cache-Aside旁路缓存.md)

## 步骤

```bash
python scripts/consistency_check.py            # 默认 3 策略 × 6s
python scripts/consistency_check.py --duration 3 --threads 8   # self_verify 用快速档
```

## 预期结果

- A 无兜底：删除失败时旧值滞留至 ttl_cap（5s 截断，真实为 ∞）
- B TTL：不一致窗口 max ≈ TTL（2s，上界保险生效）
- C 延迟双删：窗口显著压缩（≤ 删除延迟 + 回源时间）
- 三策略均无异常崩溃（daemon 线程 + join 超时防护）

## 失败纠正与修正指引

1. 某策略样本为 0：并发模型失效（先查 start 事件与 daemon 线程）。
2. B 的 max 显著超 TTL：TTL 过期检查 bug（cache.get 的 now 传参）。
3. 结论反转（A 窗口比 B 小）：测量循环被优化掉，检查 deadline 计算。
4. 修正：策略语义变更（如新增 CDC 策略）时同步更新 04.01.01 与 AI_Skill cache-architecture-patterns。

## 修正历史

- 2026-11-17 首版：Barrier 同步在 Windows 高并发下出现等待异常（超时 721s 案例）→ 改 Event 发令 + daemon 线程 + join 超时三重防护。
