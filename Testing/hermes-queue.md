# hermes 执行工作队列（执行轨唯一入口）

> 规则见 AGENTS.md §4.0 协作宪章。hermes 每次启动：① 开工自检（§例行项 0）→ ② 按下表"当前在域"推进 → ③ 完成一项走简报协议（产物 Testing/output/ + 执行记录节 + registry 流转）。**用户不指定单项任务**；新任务由主控规划入队；计划外发现登记观察区。

## 自治级别

- **A**=全自治（执行+回填+简报即可）
- **P**=执行后须主控审计抽核（1/3 回放）再算闭环
- **U**=用户门（破坏性/长耗时/正文内容变更——执行前须用户在场或已预批）

## 例行项 0（每次开工自检，A）

- `python3 Testing/08-能力矩阵/tools/env_doctor.py check --fix`（环境治理器自检：运行时 podman 唯一/镜像钉版状态/lab 容器健康+可逆修正/端口/磁盘；产物 Testing/output/env_doctor/）
- 容器运行时探测确认（容器适配规范 §1：podman 唯一；缺失→NO_CONTAINER 记录）
- `python Testing/self_verify.py all` 确认 L1 基线绿（红=先修或上报，不带病执行）

## 执行队列

| 序 | ID | 批次 | 任务 | 判据 | 级 | 依赖/解锁 | 状态 | 完成时间 |
| -- | -- | ---- | ---- | ---- | -- | -------- | ---- | -------- |
| 1 | Q-A2 | A2 | 监控全栈+告警四连（TC-OPS-005-C；podman 适配+降级路径见 §7 任务卡） | 四规则 /alerts 可见触发；回填用例执行记录 | A | prometheus 在盘；exporter/grafana 缺镜像→单栈降级 | ⬜ | |
| 2 | Q-A3 | A3 | Podman 冒烟（sentinel 环境 PING） | 三哨兵 PONG+主从角色正确 | A | redis:7-alpine 在盘 | ⬜ | |
| 3 | Q-A4 | A4 | 轮换首轮：TC-CLUS-003（Sentinel RTO）+ TC-CLUS-006（备份 RPO）+对账抽检 | 用例通过标准列；RTO/RPO 回填 07.04.03/07.05.04 | P | 哨兵栈 podman run 等价形；与 Q-A2 错开 6379 时段 | ⬜ | |
| 4 | Q-M3a | M3 | memtier 镜像获取（registry 恢复后重试）→ MX-C MTIER 半表 16 格执行 | 镜像在盘+一格试跑 | A | 网络/registry（**16 格用例实体已由主控 2026-11-21 gen 铺底完成**） | ⬜ | |
| 5 | Q-M3b | M3 | Go/Rust 客户端资产（MX-D 两行余下 14 格 ○E→●；**STR 两格已由主控 2026-11-21 编写原生用例+资产，本项余 HASH~TXLUA 扩展**）：示例+工具链实证 | go/rust 客户端对 lab redis 冒烟通过 | A | go/cargo 在盘（已具备） | ⬜ | |
| 6 | Q-M3c | M3 | trace_benchmark/kv_evict 算法扩展执行（**用例实体已 gen 铺底**：MX-A TRACE/SIM 格 24 件） | 扩展算法跑通+结果入 01.05.04 登记段 | A | 无 | ⬜ | |
| 7 | Q-M3d | M3 | Coq 环境+FIFO 竞争比引理链起手（B3 联动，MX-A FIFO×COQ 格） | coqc 编译通过记录 | P | Coq 安装 | ⬜ | |
| 8 | Q-M4 | M4 | ●格执行闭环：TC-MXE-AUTH/RENAME-LIVE 实跑 + MX-B 关联格执行记录回填 + registry seed→done | 看板 ●格执行率可统计 | P | Q-A2~A4 环境 | ⬜ | |
| 9 | Q-B1 | B1 | LLM 推理部署实践篇（章节大纲见 §7；含版本事实双源核实） | 密度 250-400 行/≥4 代码块/≥3 表；公式入对照表 | U | 无（可并行） | ⬜ | |
| 10 | Q-B2 | B2 | 英文 README 摘要（三节结构见 §7） | 根 README 互链 | U | 无（可并行） | ⬜ | |
| 11 | Q-B3 | B3 | Coq FIFO 竞争比≤2 里程碑（引理链 a→b→c 规格见 §7） | coqc 0 error+axiom 清单登记 | U | Q-M3d 环境 | ⬜ | |
| 12 | Q-C2 | C2 | cron 接线（运行器设计稿 §7：nightly 静默+周一提醒） | 实装+试跑一次 | A | 无 | ⬜ | |
| 13 | Q-C1 | C1 | L4 月度验收 12 月首跑（生成器设计稿 §7） | acceptance_2026-12.md 生成+覆盖率判定 | A | 2026-12 月末 | ⬜ | |
| 14 | Q-C3 | C3 | 季度评审 2027-02（三步模板 §7） | 对称差表刷新+断言清单扩充 | U | 2027-02 | ⬜ | |

## 执行入口映射（ID → 具体命令/判据指针；hermes 按此取件）

| ID | 执行入口 |
| -- | -------- |
| Q-A2 | §7 任务卡 A2 + `Testing/fixtures/redis-lab/monitoring-compose.yml`（podman run 等价形；exporter/grafana 缺镜像→单栈降级路径见卡内） |
| Q-A3 | `podman run` 哨兵栈等价形 + `redis-cli -p 26379..26381 SENTINEL master mymaster`（判据=卡内） |
| Q-A4 | 哨兵栈 + `Testing/cases/04-集群/TC-CLUS-003/006` 步骤（podman 适配 §2）；回填 07.04.03/07.05.04 |
| Q-M3a | `podman pull docker.io/memtier_benchmark/memtier_benchmark`（registry 恢复后；见 lab.env BC_REGISTRY_NOTE） |
| Q-M3b | `main.go/main.rs -ops <族>` 已铺 16 格；余量=PY 行 2 格（STREAM/BITMAP 文档示例锚定） |
| Q-M3c | `scripts/benchmark/trace_benchmark.py` + kv_evict 扩算法（用例格=执行规格） |
| Q-M3d | Coq 安装（Windows 安装器/opam）→ B3 引理链（§7 规格） |
| Q-M4 | `python3 Testing/08-能力矩阵/tools/mx_runner.py`（全量基线）→ 失败项逐格处置 → 回填三件套 |
| Q-B1/B2/B3 | §7 任务卡规格（章节大纲/结构/引理链）；U 级执行前须用户背书 |
| Q-C2 | §7 C2 运行器设计稿（git 受控脚本+薄壳 cron） |
| Q-C1 | §7 C1 生成器设计稿（history log + GitHub API 数据源） |
| Q-C3 | §7 C3 三步模板（对称差刷新+断言扩充+版本复核） |

**执行纪律**：FAIL 走用例修正指引；环境缺→SKIP 并登记观察区；**禁止伪造通过**；产物只写 Testing/output/。

## 依赖与并行编排

- 串行链：Q-A2→Q-A3→Q-A4（端口/环境时段）；Q-M3d→Q-B3；其余互相独立。
- 可并行组：{Q-B1, Q-B2, Q-C2}（独立文件域）；{Q-M3a, Q-M3b, Q-M3c}（独立资产）；A 链 ∥ M3 组 ∥ B/C 组。
- 取序默认：A 链先行（用户裁定 A 批优先），M3 组与 B/C 组穿插。

## 观察区（hermes 登记，主控裁定后入队）

| 登记时间 | 事项 | 状态 |
| -- | ---- | ---- |
| 2026-11-21 | redis:8-alpine 镜像源故障（daocloud DNS 失效/registry-1 拒连），基线暂为 7-alpine 口径——镜像源恢复后走 `env_doctor.py update --image redis:8-alpine --bench`（拉取→改钉→重建容器→重建基线） | 待办（触发式，无需在域等待） |
| 2026-11-21 | lab 容器 redis-bench-lab 间歇停止（env_doctor check 实证）——已 --fix 自修正；复发须查 podman machine 稳定性 | 已处置（观察） |

## 变更记录

- 2026-11-21 建队（M1/M2 后）：14 项（=§8 总览 11 项拆分 M3 为 4 子项）+例行自检；来源判据全部指向 §7 任务卡与 08-能力矩阵适用矩阵。
