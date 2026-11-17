# TC-OPS-004 弹性伸缩与自愈配置验证

- **用例ID**：TC-OPS-004 | **优先级**：P1 | **自动化**：self_verify 已覆盖（`ops`，随 07.09 文档 yaml 块扫描）
- **目的**：07.09 弹性伸缩与自愈文档中的 HPA/KEDA/探针/Chaos Mesh 配置语法合法、关键防护字段齐全
- **关联**：[07.09 弹性伸缩与自愈](../../../docs/07-运维与部署/07.09-弹性伸缩与自愈/)；[AI_Skill elastic-selfhealing](../../../AI_Skill/skills/elastic-selfhealing/SKILL.md)

## 步骤

```bash
python Testing/self_verify.py ops
# 检查项（随 ops 组执行）：
#  1. docs/07.09 全部 yaml 代码块可解析（Helm 模板豁免）
#  2. HPA/ScaledObject 示例含伸缩边界（min/max 或 minReplicaCount/maxReplicaCount）
#  3. 探针示例含 failureThreshold（防误杀关键字段）
#  4. Chaos Mesh 实验示例含爆炸半径控制（mode: one/percent 非全部）
```

## 预期结果

07.09 加入 ops 扫描路径后静态检查全过；人工核对清单见 07.09.02 §2.1 探针三件套与 §3 自愈配置表。

## 失败纠正与修正指引

1. YAML 语法错误：修正文档配置块。
2. 缺边界字段：补 min/max 副本或 failureThreshold，并注明取值依据（指向 07.09.01 §3.3 / 07.09.02 §2.1）。
3. Chaos 实验无爆炸半径：必须补 `mode: one`/`selector` 限定，生产演练还需中止条件（07.09.03 §3）。
4. 修正：新伸缩/自愈配置文档提交前必跑 `ops`；本用例失败即阻断。
