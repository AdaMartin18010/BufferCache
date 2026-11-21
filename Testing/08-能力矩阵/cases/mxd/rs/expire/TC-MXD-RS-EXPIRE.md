# TC-MXD-RS-EXPIRE Rust redis-rs 客户端对 过期与淘汰 操作族冒烟

- **用例ID**：TC-MXD-RS-EXPIRE | **优先级**：P1 | **矩阵格**：MX-D / RS / EXPIRE
- **自动化**：剧本型（gen 铺底） | **批次**：M2+ gen 2026-11-21 → enrich 充实 2026-11-21（8 操作族参数化，mx_runner 可执行）
- **运行时**：DOCKER+PODMAN｜ANY（按手段）
- **环境阻塞声明**：本格执行依赖外部资产（镜像/GPU/工具链等），未就绪时按测试框架规范 SKIP 不 FAIL，解锁后 hermes 执行
- **目的**：Rust redis-rs 客户端对 过期与淘汰 操作族冒烟
- **关联**：topics/examples / docs/03-Redis组件 03.04（维度定义 TSV 行；enrich 批从源文档派生具体数值断言）

## 前置条件

- 按关联源文档准备环境/参考实现；运行时按容器适配规范 §1 探测适配

## 步骤（GWT 五段式）

```text
# Given lab redis 在跑（密码 lab-password）与 Rust redis-rs 工具链
# When 客户端执行 过期与淘汰 族代表命令序列（CRUD+边界）
# Then 每命令响应断言成立（enrich 批按操作族定序列）
# And 连接清理无泄漏
```

## 实测断言（enrich 批 2026-11-21）

- **执行资产**：`cases/mxd/rs/str/main.rs`——stdlib RESP 客户端（零外部依赖），步骤规格=[期望,命令,参数...]（{K}=每族唯一键 runid）
- **断言序列**：SET→+OK / EXPIRE 100→:1 / TTL→TTL_POS(>0) / PERSIST→:1
- **判定**：全步骤期望匹配=PASS；任一失配=FAIL（输出 got/want 对）

## 预期结果

- 各 Then/And 断言成立（具体判定值 enrich 批充实）

## 通过标准

- gen 铺底件的通过标准 = 关联源文档的机制定义；enrich 批补充数值阈值

## 失败纠正与修正指引

1. 环境缺：SKIP 语义登记（测试框架规范铁律），解锁后重跑。
2. 机制断言 fail：先核对参考实现/配置与源文档定义的一致性（定义漂移走文档变更流程）。
3. 本文档为生成器铺底件（Mq gen→enrich 生命周期）；充实=主控 enrich 批或 hermes 执行回填，执行权归 hermes。
