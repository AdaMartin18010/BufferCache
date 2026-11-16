# scripts/formal — 缓存算法 TLA+ 形式化规约

本目录包含可执行的 TLA+ 规约，对应文档
`docs/01-理论基础/01.05-算法对比与决策/01.05.06-缓存算法TLA形式化规约.md`。

## 文件

| 文件 | 内容 |
| ---- | ---- |
| `LRU.tla` / `LRU.cfg` | LRU 替换算法规约：容量不变式、顺序一致性、MRU 语义、对象驻留活性 |
| `ARC.tla` / `ARC.cfg` | ARC 自适应替换算法规约：四列表状态机、p 自适应、论文容量约束、列表不相交性 |
| `tla2tools.jar` | TLC 模型检查器（nightly 构建，~4.5MB） |
| `run.bat` | Windows 一键运行脚本 |

## 运行方法

```bash
# Windows
run.bat

# 或手动（任意平台，需 Java 11+）
java -XX:+UseParallelGC -jar tla2tools.jar -config LRU.cfg LRU.tla
java -XX:+UseParallelGC -jar tla2tools.jar -config ARC.cfg ARC.tla
```

## 验证结果（2026-01，TLC nightly 2026.11.15）

| 模型 | 生成状态 | 不同状态 | 深度 | 性质 | 结果 |
| ---- | -------- | -------- | ---- | ---- | ---- |
| LRU（4 key，容量 2） | 69 | 17 | 3 | CapacityInv / ConsistencyInv / MruMembership / AllKeysEventuallyCached | ✅ 全部满足 |
| ARC（4 key，容量 2） | 1909 | 477 | 9 | ArcCapacityInv / GhostBoundInv / DisjointInv | ✅ 全部满足 |

## 规约要点

- **LRU**：`Hit / MissInsertNonFull / MissEvictInsert` 三动作；活性性质
  `[]<>(k ∈ cache)` 在 **强公平性** `SF_vars(PerKey(k))` 下成立
  （弱公平 `WF_vars(Next)` 不足：存在只访问部分对象的合法公平行为——
  TLC 实际给出了该反例，此为本目录规约相比文档初稿的关键修正）。
- **ARC**：`CaseI–CaseIV` 四分支完整实现 Megiddo & Modha (FAST 2003) 的
  REPLACE 过程与 p 自适应公式；`Evict(x)` 为纯函数返回四元组，
  规避 TLA+ 动作内读取 primed 变量的非法用法。
- **Min/Max**：所用 nightly 工具链的标准模块不含 Min/Max，
  规约内以 `Min2/Max2` 自给。

## 扩展更大模型

编辑 `.cfg` 中的 CONSTANTS（如 `Keys = {k1,k2,k3,k4,k5}`、`Capacity = 3`）。
状态数随 Keys 规模快速增长；ARC 建议先用 `-workers 4` 并行：

```bash
java -XX:+UseParallelGC -jar tla2tools.jar -workers 4 -config ARC.cfg ARC.tla
```
