# TC-DOC-005 多语言代码块测试（Go/Rust/Bash）

- **用例ID**：TC-DOC-005 | **优先级**：P1 | **自动化**：self_verify 已覆盖（`docs` 组）
- **目的**：docs/ 中 Go/Rust 代码块可编译运行（完整程序）、Bash 块语法合法；守住"其他语言测试"空白（AGENTS.md §5：其他语言待做 → 本用例闭合）
- **关联**：`scripts/code_test_framework.py --test go|rust|bash`；报告 `reports/code_test_report_{go,rust,bash}.md`

## 测试策略（依语言特性区分，遵守 AGENTS.md §4.2.4 平台守卫禁令）

| 语言 | 块数（2026-11） | 策略 | 跳过类别 |
| ---- | -------------- | ---- | -------- |
| Go | 14 | 完整 `package main` 程序 `go run` | 片段/第三方 import/root 权限 |
| Rust | 8 | `rustc` 编译，通过则运行 | 片段/第三方 crate/E04xx 未定义符号 |
| Bash | 189 | `bash -n` 语法检查（**不执行**） | 过短片段/`<placeholder>` 占位 |

## 步骤

```bash
python scripts/code_test_framework.py --test go
python scripts/code_test_framework.py --test rust
python scripts/code_test_framework.py --test bash
```

## 预期结果

三种语言"测试失败"均为 0（当前基线：Go 8 过、Rust 5 过、Bash 146 过，各含合理跳过）。

## 失败纠正与修正指引

1. Go/Rust 编译错误：修正文档代码块（历史已修：缺 import 3 处、unused import 1 处、泛型缺 Debug 约束 1 处）。
2. 片段被误判为完整程序：改进启发式（如新增跳过类别），不要为通过测试而删改教学代码语义。
3. Bash 语法错误：修正文档脚本（历史已修：一行两语句 1 处）；`<placeholder>` 伪参数属正常文档惯例，应跳过而非修改。
4. 修正（防复发）：启发式变更必须复跑三种语言全量确认无误判；本用例纳入 `self_verify.py all`。

## 修正历史

- 2026-11-17 首测：Go 4 失败 / Rust 3 失败 / Bash 4 失败 → 修文档缺陷 5 处 + 启发式 5 处 → 三语言 0 失败基线建立
