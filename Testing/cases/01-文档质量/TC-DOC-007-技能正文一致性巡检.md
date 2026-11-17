# TC-DOC-007 技能-正文一致性巡检

- **用例ID**：TC-DOC-007 | **优先级**：P1 | **自动化**：self_verify 已覆盖（`docs` 组）
- **目的**：事实断言清单驱动的双端比对——技能 §2/§3 的关键事实与 docs 正文逐条核对，发现"技能说 A、正文说 B"的静默漂移（第四道内容门禁的自动化执行器）
- **关联**：[scripts/assertion_check.py](../../scripts/assertion_check.py)；[事实断言清单](../../docs/00-项目总览/事实断言清单.md)

## 步骤

```bash
python scripts/assertion_check.py            # 全量巡检
python scripts/assertion_check.py --fix-report   # 输出报告
```

## 预期结果

全部 PASS。检查项断言对（CHECKS 列表）随事实断言清单扩充而增加。

## 失败纠正与修正指引

1. DRIFT：定位三端（技能/正文/清单）哪端错——以权威来源索引仲裁；本轮实战案例：01.02.10 正文 SIEVE 出处误写 "ATC 2024"（正确 NSDI 2024），巡检发现后已修。
2. 新漂移模式：向 CHECKS 增加新断言对（技能文件、技能侧关键词、正文文件、正文侧关键词）。
3. 修正：本检查项失败即阻断提交；修复后同步更新事实断言清单"最后核验"日期。
