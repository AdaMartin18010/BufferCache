# TC-DOC-002 代码块语言标注真实性

- **用例ID**：TC-DOC-002 | **优先级**：P0 | **自动化**：self_verify 已覆盖（`docs`）
- **目的**：禁止把非 Python 内容标注为 `python`（历史曾发生 4 处：Prometheus 查询须 `promql`、配置须 `ini`/`yaml`、伪代码须 `text`，见 [AGENTS.md](../AGENTS.md) §3.3）
- **关联**：docs/ 全库代码块

## 步骤

```bash
python Testing/self_verify.py docs
# 检查项：扫描 docs/ 全部 ```lang 标注与内容指纹（如 prometheus 表达式、yaml 键、伪代码关键词）
```

## 预期结果

无非 Python 内容标为 `python`；`promql`/`ini`/`yaml`/`text` 使用符合 §3.3。

## 失败纠正与修正指引

1. 纠正：把虚假 `python` 标注改为真实语言（参考同文档其他块或内容特征）。
2. 修正：在文档质量标准中重申该条；评审新文档时把语言标注列入核对项。
3. 复跑 `python Testing/self_verify.py docs` 转绿。
