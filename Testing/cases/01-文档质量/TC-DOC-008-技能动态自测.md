# TC-DOC-008 技能动态自测

- **用例ID**：TC-DOC-008 | **优先级**：P1 | **自动化**：self_verify 已覆盖（`skilltest` 组，slow）
- **目的**：20 个 AI 技能的 §7 验证命令**真实执行**（与 assertion_check 静态巡检互补成"静态+动态"双检）——技能承诺的能力必须可运行
- **关联**：[scripts/skill_selftest.py](../../../scripts/skill_selftest.py)；[TC-DOC-007](TC-DOC-007-技能正文一致性巡检.md)

## 步骤

```bash
python scripts/skill_selftest.py                 # 全量 20 技能
python scripts/skill_selftest.py --skill llm-kv-cache
```

## 预期结果

20 PASS / 0 FAIL（当前基线）；白名单外命令不执行（安全边界）。

## 失败纠正与修正指引

1. FAIL：技能 §7 命令失效或输出漂移——修技能文档或修脚本断言（判定：命令是否仍然有效）。
2. 新技能：在 SKILL_COMMANDS 登记（**只允许只读命令**：测试/检查/报告类；写操作/网络操作禁止入内）。
3. 修正：技能 §7 与 SKILL_COMMANDS 双向同步（技能改命令→脚本必改，由本用例红线保证）。
