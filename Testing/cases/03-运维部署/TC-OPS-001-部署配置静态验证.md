# TC-OPS-001 部署配置静态验证

- **用例ID**：TC-OPS-001 | **优先级**：P1 | **自动化**：self_verify 已覆盖（`ops`，环境缺工具时跳过并标注）
- **目的**：docs/07 中的 Ansible/Terraform/Helm/compose 配置在变更前后均通过静态验证，坏配置不进主干
- **关联**：[07.01](../../../docs/07-运维与部署/07.01-部署自动化/)；[AI_Skill cache-operations-testing](../../../AI_Skill/skills/cache-operations-testing/SKILL.md) §3

## 前置条件

按需安装：terraform、ansible、helm（self_verify 自动探测，缺则该子项标 SKIP）。

## 步骤

```bash
python Testing/self_verify.py ops
# 对 docs/07 与 AI_Skill/Testing 下发现的配置文件执行：
#   terraform validate / fmt -check
#   ansible-playbook --syntax-check
#   helm lint / helm template
#   yaml.safe_load 全量 YAML 解析
```

## 预期结果

已安装工具的子项 0 错误；YAML 全量可解析；SKIP 子项明确列出。

## 失败纠正与修正指引

1. 语法错误：修正文档中的配置块（注意代码块完整性，避免截断片段被当完整配置——片段应在文档声明用途）。
2. 版本漂移（如 `apiVersion` 过期）：按官方当前版本更新并注明。
3. 修正：新配置类文档提交前必跑 `ops`；把本用例命令写入 07.01 各文档"验证"节。
4. 复跑转绿。
