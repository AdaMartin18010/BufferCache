# TC-STAT-001 文档统计口径

- **用例ID**：TC-STAT-001 | **优先级**：P2 | **自动化**：self_verify 已覆盖（`structure`）
- **目的**：文档统计口径唯一且与实际目录一致（AGENTS.md §5-5；STATUS.md 计数）
- **关联**：[STATUS.md](../docs/00-项目总览/STATUS.md)；[docs/INDEX.md](../docs/INDEX.md)

## 步骤

```bash
python Testing/self_verify.py structure
# 检查项：find docs -name "*.md" -not -path "*/archive/*" | wc -l 的口径
# 与 STATUS.md 声明计数一致（AI_Skill/Testing 不计入 docs 口径，单独统计）
```

## 预期结果

- docs/ 计数 = STATUS.md 声明值（含明确标注的容差说明）。
- AI_Skill/ 与 Testing/ 文件数单独报告，不混入 docs 口径。

## 失败纠正与修正指引

1. 计数差 = 新增文档数：补 STATUS.md 计数与变更记录。
2. 计数差 ≠ 新增数：查 archive/ 是否误入口径、重复主题目录。
3. 修正：统计逻辑集中在 self_verify.py，不再多处手写 `find | wc`（文档中引用口径时指向本用例）。
4. 复跑转绿。
