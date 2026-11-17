# TC-DOC-001 文档代码块可运行性

- **用例ID**：TC-DOC-001 | **优先级**：P0 | **自动化**：self_verify 已覆盖（`docs`）
- **目的**：保证 docs/ 全部 Python 代码块可运行，守住"代码测试 100%"基线
- **关联**：AGENTS.md §5-1；[AI_Skill 技能 §7](../../../AI_Skill/README.md) 各技能验证命令；[docs/00-项目总览/代码示例测试框架.md](../../../docs/00-项目总览/代码示例测试框架.md)

## 前置条件

Python 3.8+；Windows 环境需 Git Bash（项目约定环境）。

## 步骤

```bash
python scripts/code_test_framework.py --test python
```

## 预期结果

`0 失败`（通过 + 环境依赖/上下文片段跳过为正常分类）；任何"真实错误"类别为 0。

## 失败纠正与修正指引

1. 读失败分类：依赖缺失→补 try-import 守卫；上下文片段→在文档中显式声明"函数级教学片段"；平台问题→按 [AGENTS.md](../../../AGENTS.md) §4.2.4 加 `sys.platform` 守卫。
2. 真实语法/逻辑错误：修正文档代码块本身。
3. 修正（防复发）：同类守卫模式补入 [AI_Skill/SKILL规范.md](../../../AI_Skill/SKILL规范.md) §3.3；新失败模式在 code_test_framework.py 中增加分类。
4. 复跑 `python Testing/self_verify.py docs` 转绿。
