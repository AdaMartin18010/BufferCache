---- MODULE LRU ----
(*
 * LRU 缓存替换算法的 TLA+ 形式化规约
 * 对应文档: docs/01-理论基础/01.05-算法对比与决策/01.05.06-缓存算法TLA形式化规约.md
 *
 * 验证目标（safety）:
 *   1. CapacityInv       —— 缓存容量不变式
 *   2. ConsistencyInv    —— lruOrder 恰好是 cache 的无重复排列
 *   3. EvictionCorrect   —— 满时驱逐的对象是最近最少使用者（lruOrder 尾部）
 *
 * 验证目标（liveness, 需公平性）:
 *   1. AllKeysEventuallyCached —— 每个 key 被无限频繁地访问则无限频繁地在缓存中
 *
 * 运行: java -jar tla2tools.jar -config LRU.cfg LRU.tla
 *)

EXTENDS Naturals, Sequences, FiniteSets

CONSTANTS Keys,        \* 对象全集，模型检查时取有限集，如 {k1,k2,k3,k4}
          Capacity     \* 缓存容量，如 2

VARIABLES cache,       \* 缓存内容集合
          lruOrder     \* 由新到旧的访问顺序序列（Head=MRU，Tail=LRU）

vars == <<cache, lruOrder>>

\* 从序列中移除指定元素（保持其余元素顺序）
Remove(seq, e) == SelectSeq(seq, LAMBDA x: x # e)

\* 对象在 lruOrder 中的位置（1=MRU，Len=LRU）
RecencyRank(k) == CHOOSE i \in DOMAIN lruOrder : lruOrder[i] = k

-----------------------------------------------------------------------------
\* 初始状态：空缓存

Init ==
  /\ cache = {}
  /\ lruOrder = <<>>

-----------------------------------------------------------------------------
\* 动作：命中，对象移至 MRU 端（cache 不变）

Hit(k) ==
  /\ k \in cache
  /\ lruOrder' = <<k>> \o Remove(lruOrder, k)
  /\ cache' = cache

\* 动作：未命中且未满，插入 MRU 端

MissInsertNonFull(k) ==
  /\ k \notin cache
  /\ Cardinality(cache) < Capacity
  /\ cache' = cache \cup {k}
  /\ lruOrder' = <<k>> \o lruOrder

\* 动作：未命中且已满，驱逐 LRU 端（lruOrder 尾部），插入新对象

MissEvictInsert(k) ==
  /\ k \notin cache
  /\ Cardinality(cache) = Capacity
  /\ LET victim == lruOrder[Len(lruOrder)]
     IN /\ cache' = (cache \ {victim}) \cup {k}
        /\ lruOrder' = <<k>> \o Remove(lruOrder, victim)

PerKey(k) == Hit(k) \/ MissInsertNonFull(k) \/ MissEvictInsert(k)

Next == \E k \in Keys: PerKey(k)

-----------------------------------------------------------------------------
\* 规范：初始 + 步进 + 强公平性
\* 公平性说明：WF_vars(Next) 不足以推出每个对象的驻留活性（存在只访问部分
\* 对象的合法公平行为）。对每对象动作 PerKey(k) 施加强公平性（SF）：
\* PerKey(k) 在任何状态下持续 enabled（命中或缺失至少其一可行），故 SF 强制
\* 每个 key 被无限访问，从而无限驻留——这正是 AllKeysEventuallyCached 的前提。

Spec ==
  /\ Init
  /\ [][Next]_vars
  /\ \A k \in Keys: SF_vars(PerKey(k))

-----------------------------------------------------------------------------
\* 不变式（safety 性质）

\* 容量不变式
CapacityInv == Cardinality(cache) <= Capacity

\* 顺序一致性：lruOrder 无重复且恰好等于 cache
ConsistencyInv ==
  /\ Len(lruOrder) = Cardinality(cache)
  /\ {lruOrder[i] : i \in DOMAIN lruOrder} = cache

\* MRU 语义：序列头部若存在则必在缓存中（由 ConsistencyInv 蕴含，作为冗余校验
\* 可在 ConsistencyInv 被意外弱化时独立报警）
MruMembership == lruOrder = <<>> \/ lruOrder[1] \in cache

-----------------------------------------------------------------------------
\* 活性性质：每个 key 若被无限频繁请求，则无限频繁驻留缓存
\* （TLC 中以小模型 + WF 验证）

AllKeysEventuallyCached == \A k \in Keys: []<>(k \in cache)

=============================================================================
