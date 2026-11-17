# TC-DOC-004 导航与索引同步完整性

- **用例ID**：TC-DOC-004 | **优先级**：P0 | **自动化**：self_verify 已覆盖（`structure`）
- **目的**：新增/移动/重命名文档后，所属 README、docs/INDEX.md、STATUS.md 计数保持同步（[AGENTS.md](../../../AGENTS.md) §7 变更同步义务）
- **关联**：docs/INDEX.md；各主题 README；STATUS.md

## 步骤

```bash
python Testing/self_verify.py structure
# 检查项：
#  1. INDEX.md 引用的每个 .md 文件存在
#  2. 每个 docs/ 子目录存在 README.md（导航完整性）
#  3. 实际文档数与 STATUS.md 声明计数一致（容差：STATUS 明确标注的归档排除）
#  4. AI_Skill/skills 各技能目录存在 SKILL.md 且 name 与目录名一致
```

## 预期结果

四项全过；计数差值有明确解释（如新增未登记）。

## 失败纠正与修正指引

1. 纠正：把新文档挂入所属子目录 README 与 INDEX.md（正文+目录区）；更新 STATUS.md 计数与变更记录。
2. 编号漂移（文档号与子主题不符）：按 [AGENTS.md](../../../AGENTS.md) §3.1 规则改名并同步全部引用。
3. 修正：把"未挂导航的新文档"加入 structure 检查的失败类别，防止再发生。
4. 复跑 `python Testing/self_verify.py structure` 转绿。
