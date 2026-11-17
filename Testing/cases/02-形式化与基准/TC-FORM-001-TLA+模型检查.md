# TC-FORM-001 TLA+ 模型检查

- **用例ID**：TC-FORM-001 | **优先级**：P1 | **自动化**：self_verify 已覆盖（`formal`）
- **目的**：LRU/ARC 规约的 TLC 模型检查全性质通过，守住形式化资产有效性
- **关联**：[scripts/formal/](../scripts/formal/)；[01.05.06](../../docs/01-理论基础/01.05-算法对比与决策/01.05.06-缓存算法TLA形式化规约.md)

## 前置条件

Windows：直接运行（项目自带 run.bat）；Linux/macOS：需 Java + tlc2tools.jar。

## 步骤

```bash
scripts/formal/run.bat          # Windows
# 或 Linux/macOS：
java -XX:+UseParallelGC -cp scripts/formal/tla2tools.jar tlc2.TLC scripts/formal/LRU.tla -config scripts/formal/LRU.cfg
java -XX:+UseParallelGC -cp scripts/formal/tla2tools.jar tlc2.TLC scripts/formal/ARC.tla -config scripts/formal/ARC.cfg
```

## 预期结果

LRU（69 状态）与 ARC（1909 状态）全部不变量与活性性质通过；无错误轨迹。

## 失败纠正与修正指引

1. 不变量失败：规约与文档描述不一致——以文档算法定义为准修正规约，或修订文档（登记 STATUS.md）。
2. 活性失败：检查公平性假设（项目历史教训：WF 会漏报，必须用 SF，见 01.05.06）。
3. 状态数异常膨胀：检查变量上界配置（.cfg 的 Const 赋值）。
4. 修正：规约变更后同步更新 01.05.06 的验证结果表。
5. 复跑 `python Testing/self_verify.py formal` 转绿。

## 已知边界

只覆盖单进程抽象；并发驱逐、持久化交互未建模（已在 01.05.06 声明）。
