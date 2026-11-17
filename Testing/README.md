# Testing — BufferCache 项目测试与验证体系

> 本目录是项目的**测试用例库与自我验证机制**：把 [AGENTS.md](../AGENTS.md) §5 工具链、运维部署、集群、CI 集成等验证要求用例化，并提供统一入口 `self_verify.py` 自动执行与诊断。

## 1. 体系结构

```text
Testing/
├── README.md                  # 本文件
├── 自我验证修正机制.md         # 验证→诊断→纠正→修正→回归→登记 闭环机制
├── self_verify.py             # 统一自我验证入口（聚合执行 + 报告 + 修复指引）
└── cases/                     # 测试用例库（五组 15 个用例）
    ├── 01-文档质量/
    │   ├── TC-DOC-001-文档代码块可运行性.md
    │   ├── TC-DOC-002-代码块语言标注真实性.md
    │   ├── TC-DOC-003-相对链接完整性.md
    │   └── TC-DOC-004-导航与索引同步完整性.md
    ├── 02-形式化与基准/
    │   ├── TC-FORM-001-TLA+模型检查.md
    │   ├── TC-BENCH-001-Trace驱动算法基准.md
    │   ├── TC-BENCH-002-KV前缀缓存模拟实验.md
    │   └── TC-STAT-001-文档统计口径.md
    ├── 03-运维部署/
    │   ├── TC-OPS-001-部署配置静态验证.md
    │   ├── TC-OPS-002-Prometheus规则与告警验证.md
    │   └── TC-OPS-003-缓存安全基线检查.md
    ├── 04-集群/
    │   ├── TC-CLUS-001-RedisCluster部署与槽覆盖.md
    │   ├── TC-CLUS-002-复制链路健康验证.md
    │   ├── TC-CLUS-003-Sentinel故障转移演练.md
    │   └── TC-CLUS-004-Cluster故障转移与恢复.md
    └── 05-集成/
        ├── TC-INT-001-全量自我验证回归.md
        └── TC-INT-002-CI集成与版本监控.md
```

## 2. 用例统一模板

每个用例文件包含：用例ID / 优先级 / 自动化状态（self_verify 已覆盖·部分覆盖·人工）/ 目的 / 前置条件 / 步骤与命令 / 预期结果 / **失败纠正与修正指引** / 关联（AI_Skill 技能 §7、docs 文档）。

- **纠正（correct）**：让本次验证通过的操作（如修复失效链接）。
- **修正（fix）**：消除根因防复发（如把链接检查加入提交前必跑）。

## 3. 运行方式

```bash
python Testing/self_verify.py all          # 全量（文档质量+形式化基准+结构；CI 默认）
python Testing/self_verify.py docs         # 文档质量组（代码块/标注/链接/导航/统计）
python Testing/self_verify.py links        # 仅链接完整性（支持 --path 限定目录）
python Testing/self_verify.py formal       # TLA+ 模型检查（Windows 自动调 run.bat）
python Testing/self_verify.py bench        # Trace 基准 + KV 模拟
python Testing/self_verify.py ops          # 运维配置静态验证（环境缺工具时自动跳过并标注）
python Testing/self_verify.py structure    # 目录结构/导航一致性
python Testing/self_verify.py cluster      # 集群用例（人工步骤清单导出，供演练执行）
python Testing/self_verify.py --ci         # CI 模式：失败以非零码退出
python Testing/self_verify.py --report     # 查看最近一次报告
```

退出码：`0` 全部通过；`1` 存在失败；`2` 环境不满足（如缺 Java/Redis）。

## 4. 失败处理流程

```text
红 → 1. 读用例文件的"失败纠正与修正指引"
   → 2. 按指引纠正（修复本次问题）
   → 3. 判断是否需要修正（防复发：改模板/加守卫/更新 AGENTS.md）
   → 4. 复跑 python Testing/self_verify.py <子集> 确认转绿
   → 5. 影响范围大的登记 STATUS.md 变更记录
```

禁止行为：跳过失败直接提交；手工改动测试产物伪装通过；在 docs/ 正文粘贴测试输出（报告归 self_verify 输出目录，且被 .gitignore 忽略）。

## 5. 与其他资产的关系

| 资产 | 关系 |
| ---- | ---- |
| [AGENTS.md](../AGENTS.md) §5 | 本库把 §5 五条验证命令全部用例化（TC-DOC-001/TC-FORM-001/TC-BENCH-001/TC-LINK） |
| [AI_Skill](../AI_Skill/README.md) | 每个技能 §7 验证命令对应本库用例 ID，双向可溯 |
| [docs/](../docs/) | 07 运维/集群文档的步骤已映射为 TC-OPS/TC-CLUS 用例 |
| [scripts/](../scripts/) | self_verify 调用 code_test_framework.py、trace_benchmark.py、version_monitor.py，不复制其逻辑 |
| [reports/](../reports/) | 存量报告为历史快照；现行结果以 self_verify 输出为准 |

## 6. 新增用例规范

1. 按 §2 模板建文件，放入对应分组目录；ID 递增（组内不重号）。
2. 能被脚本判定的步骤在 self_verify.py 中实现（注册为检查项），不能的标"（人工）"。
3. 新用例必须能被 `python Testing/self_verify.py all` 或其子集触达。
4. 同步更新本 README 结构图与 [自我验证修正机制.md](自我验证修正机制.md) 的频率表。

---

**创建**：2026-11 | **维护**：与 AGENTS.md §5 工具链同步演进
