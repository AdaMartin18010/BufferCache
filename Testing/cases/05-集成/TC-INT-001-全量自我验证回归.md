# TC-INT-001 全量自我验证回归

- **用例ID**：TC-INT-001 | **优先级**：P0 | **自动化**：self_verify 已覆盖（`all`）
- **目的**：任何变更提交前，项目全量验证无回归（AGENTS.md §4.3 DoD 的验证底座）
- **关联**：[自我验证修正机制](../../../Testing/自我验证修正机制.md)；[Testing/README](../../../README.md) §3

## 步骤

```bash
python Testing/self_verify.py all          # 本地提交前
python Testing/self_verify.py all --ci     # CI 流水线（失败非零退出）
python Testing/self_verify.py --report     # 查看最近报告
```

## 预期结果

所有已覆盖检查项 PASS；SKIP 项仅为环境缺失（Java/Redis/terraform 等）且明确列出；退出码 0。

## 失败纠正与修正指引

1. 按失败项的用例 ID 打开对应 cases 文件执行修正指引（TC-DOC/TC-LINK/TC-STAT/TC-OPS 等）。
2. 失败项与本次变更无关（存量问题）：先登记 STATUS.md 待办，不得伪装通过；紧急修复优先。
3. self_verify.py 自身缺陷：修脚本并补回归（本用例即为脚本回归网）。
4. 修正：分析失败根因，把新的"防复发动作"写入机制文档 §2 对应层。
