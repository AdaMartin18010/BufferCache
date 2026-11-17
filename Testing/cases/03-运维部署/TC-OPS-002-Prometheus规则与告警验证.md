# TC-OPS-002 Prometheus 规则与告警验证

- **用例ID**：TC-OPS-002 | **优先级**：P1 | **自动化**：self_verify 已覆盖（`ops` 的 `promtool` 子项；无 promtool 时降级为 YAML+表达式静态检查）
- **目的**：docs/07.03 与 04.04.07 的告警规则语法合法、表达式可解析、告警有对应处置文档
- **关联**：[07.03.03](../../docs/07-运维与部署/07.03-监控告警/07.03.03-告警规则与通知.md)；[04.04.07](../../docs/04-架构设计/04.04-缓存问题与治理/04.04.07-缓存监控指标体系.md)

## 步骤

```bash
python Testing/self_verify.py ops
# 检查项：
#  1. promtool check rules（若可用）
#  2. 规则 YAML 解析 + 必备字段（alert/expr/for/labels/annotations）
#  3. 每条告警的 annotations 含 runbook 链接或指向 07.04 应急预案章节
```

## 预期结果

语法合法；每条告警有处置路径；命中率/内存/复制/持久化四类核心告警齐全。

## 失败纠正与修正指引

1. 表达式错误：对照 Prometheus 文档修正（注意 range-vector 必须配聚合函数）。
2. 缺处置路径：在 07.04.03 应急预案补对应小节并回链。
3. 修正：新告警入文档时强制 annotations.runbook 字段；本检查失败即阻断。
4. 复跑转绿。
