# TC-DOC-003 相对链接完整性

- **用例ID**：TC-DOC-003 | **优先级**：P0 | **自动化**：self_verify 已覆盖（`links`）
- **目的**：全部 Markdown 相对链接（含图片）可解析到真实文件，无死链
- **关联**：执行计划质量门禁 §3；新增 AI_Skill 技能提交前必查（[AI_Skill/SKILL规范.md](../../../AI_Skill/SKILL规范.md) §4.2）

## 步骤

```bash
python Testing/self_verify.py links                    # 全库
python Testing/self_verify.py links --path AI_Skill    # 限定目录（新增技能场景）
python Testing/self_verify.py links --path Testing
```

## 预期结果

死链数 0（外部 http 链接跳过但计数提示；锚点链接仅校验文档存在）。

## 失败纠正与修正指引

1. 纠正：修正路径（大小写、编号漂移）或恢复被删目标文档；archive/ 内文档不得作为链接目标（[AGENTS.md](../../../AGENTS.md) §4.2.2）。
2. 若是重命名文档导致批量断链：先 `git log --follow` 确认新位置，再全局替换。
3. 修正：新文档提交前把 `links --path <目录>` 加入提交习惯；INDEX/README 改动后必跑全量 links。
4. 复跑转绿。
