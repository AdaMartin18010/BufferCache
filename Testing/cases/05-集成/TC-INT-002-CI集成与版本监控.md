# TC-INT-002 CI 集成与版本监控

- **用例ID**：TC-INT-002 | **优先级**：P2 | **自动化**：self_verify 已覆盖（`version` 子命令）；CI 已接线（`.github/workflows/verify.yml`）
- **目的**：CI 流水线接入 self_verify；版本监控与季度前沿评审机制化
- **关联**：[scripts/version_monitor.py](../../../scripts/version_monitor.py)；[执行计划第三批](../../../docs/06-扩展计划/国际前沿对齐与质量治理执行计划.md) §4.3；[.github/workflows/verify.yml](../../../.github/workflows/verify.yml)

## 步骤

### CI 接线（已完成 2026-11-17）

`.github/workflows/verify.yml` 已创建：push/PR 触发 `python Testing/self_verify.py all --ci`（含 Java 跑 TLA+、terraform/helm/ansible/promtool 增强检查），报告以 artifact 保留 30 天。

### 版本监控（季度）

```bash
python scripts/version_monitor.py --check-all     # 需网络；人工或 CI 定时
```

## 预期结果

CI 中 self_verify 失败即阻断合并；version_monitor 输出与 [AI_Skill redis-ecosystem-versions](../../../AI_Skill/skills/redis-ecosystem-versions/SKILL.md) §6 的事实一致或触发更新。

## 失败纠正与修正指引

1. CI 红灯：按 TC-INT-001 流程处理。
2. 版本监控发现新版本：按执行计划 §5 对称差流程更新技能 §6、权威来源索引、STATUS.md 变更记录。
3. 修正：每季度评审后在本用例记录执行日期（最近：2026-11-17）。
