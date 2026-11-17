---- MODULE SIEVE ----
(*
 * SIEVE 缓存替换算法的 TLA+ 形式化规约（NSDI 2024, Zhang et al.）
 * 对应文档: docs/01-理论基础/01.02-高级替换算法/01.02.10-S3-FIFO与SIEVE算法.md
 *
 * SIEVE 核心机制（单队列 + visited 位 + hand 指针）：
 *   - 命中：仅置 visited=1（不动队列位置）
 *   - miss 未满：入队尾，visited=0
 *   - miss 已满：从 hand 位置环形扫描——visited=1 的清 0 并跳过，
 *     visited=0 的淘汰；hand 停留在淘汰位置（删除后后继占据该下标）；
 *     新对象入队尾
 *
 * 验证目标（safety）:
 *   1. CapacityInv     —— 缓存容量不变式
 *   2. ConsistencyInv  —— queue 恰好是 cache 的无重复排列
 *   3. HandInRange     —— 驱逐指针始终在合法范围（含空队列的 Len+1 哨兵）
 *   4. VisitSubset     —— visited 集合是 cache 的子集（不悬空标记）
 *
 * 验证目标（liveness，强公平性）:
 *   1. AllKeysEventuallyCached —— 每个 key 被无限频繁访问则无限频繁驻留
 *
 * 运行: java -jar tla2tools.jar -config SIEVE.cfg SIEVE.tla
 *)

EXTENDS Naturals, Sequences, FiniteSets

CONSTANTS Keys,        \* 对象全集，模型检查时取有限集，如 {k1,k2,k3,k4}
          Capacity     \* 缓存容量，如 3

VARIABLES cache,       \* 缓存内容集合
          queue,       \* FIFO 队列（Head=最老，Tail=最新）
          visited,     \* visited=1 的对象集合（visited 位的集合抽象）
          hand         \* 驱逐扫描起点下标（1..Len(queue)+1；Len+1 表示回绕到队首）

vars == <<cache, queue, visited, hand>>

\* 从序列中移除指定元素（保持其余元素顺序）
Remove(seq, e) == SelectSeq(seq, LAMBDA x: x # e)

-----------------------------------------------------------------------------
\* 驱逐扫描：从 hand 起环形查找第一个 visited=FALSE 的下标。
\* 第一遍（round=0）将 visited=1 清 0 并跳过；若整圈皆被清过（round 变 1），
\* 首个必为已清 0 者——必然终止（SIEVE 论文的 hand 循环论证）。

RECURSIVE ScanFrom(_, _, _)

ScanFrom(i, cleared, origLen) ==
  IF Len(queue) = 0 THEN 1
  ELSE LET j == IF i > Len(queue) THEN 1 ELSE i
          \* 已途经者（cleared）视为"本轮已清 0"，visited 原值不再判定
          isClear(k) == ~(k \in visited) \/ (k \in cleared)
       IN IF isClear(queue[j]) THEN j
          ELSE IF j = Len(queue)
               THEN ScanFrom(1, cleared \cup {queue[j]}, origLen)
               ELSE ScanFrom(j + 1, cleared \cup {queue[j]}, origLen)

\* 执行一次驱逐：选定 victim 下标，从 queue/cache 删除，
\* 途经被清 0 的 visited 位在动作内统一更新。
EvictVictim ==
  LET victimIdx == ScanFrom(hand, {}, Len(queue))
      victim    == queue[victimIdx]
      \* 途经点：hand 到 victimIdx（含）之间 visited=1 者（环形展开到线性区间）
      linear(h, v) == IF h <= v THEN SubSeq(queue, h, v)
                        ELSE SubSeq(queue, h, Len(queue)) \o SubSeq(queue, 1, v)
      passed    == {linear(hand, victimIdx)[i] : i \in DOMAIN linear(hand, victimIdx)}
  IN <<victim, passed>>

-----------------------------------------------------------------------------
\* 初始状态：空缓存，hand 指向队首

Init ==
  /\ cache = {}
  /\ queue = <<>>
  /\ visited = {}
  /\ hand = 1

-----------------------------------------------------------------------------
\* 动作：命中，仅置 visited=1（位置不动）

Hit(k) ==
  /\ k \in cache
  /\ visited' = visited \cup {k}
  /\ UNCHANGED <<cache, queue, hand>>

\* 动作：未命中且未满，入队尾（visited=0）

MissInsertNonFull(k) ==
  /\ k \notin cache
  /\ Cardinality(cache) < Capacity
  /\ cache' = cache \cup {k}
  /\ queue' = Append(queue, k)
  /\ visited' = visited \ {k}        \* 防御性：新对象 visited=0
  /\ hand' = hand

\* 动作：未命中且已满——SIEVE 驱逐 + 插入

MissEvictInsert(k) ==
  /\ k \notin cache
  /\ Cardinality(cache) = Capacity
  /\ LET ev == EvictVictim
         victim == ev[1]
         passed == ev[2]
         newLen == Len(queue) - 1
         victimIdx == ScanFrom(hand, {}, Len(queue))
     IN /\ cache' = (cache \ {victim}) \cup {k}
        /\ queue' = Append(Remove(queue, victim), k)
        /\ visited' = ((visited \ passed) \ {victim}) \ {k}
        \* hand 停留在 victim 原下标（删除后后继占据该位）；越界则回绕队首
        /\ hand' = IF victimIdx > newLen THEN 1 ELSE victimIdx

PerKey(k) == Hit(k) \/ MissInsertNonFull(k) \/ MissEvictInsert(k)

Next == \E k \in Keys: PerKey(k)

-----------------------------------------------------------------------------
\* 规范：初始 + 步进 + 强公平性（同 LRU 的活性前提论证）

Spec ==
  /\ Init
  /\ [][Next]_vars
  /\ \A k \in Keys: SF_vars(PerKey(k))

-----------------------------------------------------------------------------
\* 不变式（safety 性质）

CapacityInv == Cardinality(cache) <= Capacity

ConsistencyInv ==
  /\ Len(queue) = Cardinality(cache)
  /\ {queue[i] : i \in DOMAIN queue} = cache

HandInRange ==
  /\ hand \in Nat
  /\ hand >= 1
  /\ hand <= Len(queue) + 1

VisitSubset == visited \subseteq cache

-----------------------------------------------------------------------------
\* 活性性质：每个 key 被无限频繁请求则无限频繁驻留

AllKeysEventuallyCached == \A k \in Keys: []<>(k \in cache)

=============================================================================
