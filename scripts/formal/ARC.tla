---- MODULE ARC ----
(*
 * ARC 自适应替换缓存的 TLA+ 形式化规约
 * 对应文档: docs/01-理论基础/01.05-算法对比与决策/01.05.06-缓存算法TLA形式化规约.md
 *
 * 实现 Megiddo & Modha (FAST 2003) 的核心状态机:
 *   T1: 冷列表（seen once，序列 Head=MRU, Tail=LRU）
 *   T2: 热列表（seen twice+，序列 Head=MRU, Tail=LRU）
 *   B1: T1 幽灵列表（仅存 key，不存数据）
 *   B2: T2 幽灵列表（仅存 key，不存数据）
 *   p:  T1 的目标大小，B1/B2 命中自适应调整
 *
 * 验证目标（safety，INVARIANT）:
 *   1. ArcCapacityInv  —— |T1|+|T2| <= c
 *   2. GhostBoundInv   —— |T1|+|B1| <= c 且 |T2|+|B2| <= 2c（论文 4.2 节约束）
 *   3. DisjointInv     —— T1,T2,B1,B2 两两不相交
 *
 * 运行: java -jar tla2tools.jar -config ARC.cfg ARC.tla
 *)

EXTENDS Naturals, Sequences, FiniteSets, TLC

CONSTANTS Keys,        \* 对象全集
          Capacity     \* 缓存容量 c（> 0）

VARIABLES T1, T2,      \* 常驻列表
          B1, B2,      \* 幽灵列表
          p            \* T1 目标大小

vars == <<T1, T2, B1, B2, p>>

-----------------------------------------------------------------------------
\* 辅助定义

In(seq, e)     == \E i \in DOMAIN seq : seq[i] = e
Remove(seq, e) == SelectSeq(seq, LAMBDA x: x # e)
TotalCache     == Len(T1) + Len(T2)

\* 二元最大/最小（标准模块 Naturals/FiniteSets/TLC 均无 Min/Max，本模块自给）
Max2(a, b) == IF a >= b THEN a ELSE b
Min2(a, b) == IF a <= b THEN a ELSE b

\* 驱逐子计算（纯函数，返回 <<newT1, newT2, newB1, newB2>>）：
\* 依据 ARC 论文 REPLACE 过程——
\* 若 |T1|>=1 且 (|T1|>p 或 x 曾在 B2)，从 T1 尾驱逐到 B1 头；否则从 T2 尾驱逐到 B2 头
Evict(x) ==
  IF (Len(T1) >= 1) /\ ((Len(T1) > p) \/ In(B2, x))
  THEN << Remove(T1, T1[Len(T1)]),
          T2,
          <<T1[Len(T1)]>> \o B1,
          B2 >>
  ELSE << T1,
          Remove(T2, T2[Len(T2)]),
          B1,
          <<T2[Len(T2)]>> \o B2 >>

-----------------------------------------------------------------------------
\* 初始状态

Init ==
  /\ T1 = <<>>
  /\ T2 = <<>>
  /\ B1 = <<>>
  /\ B2 = <<>>
  /\ p = 0

-----------------------------------------------------------------------------
\* CASE I: x 在 T1 或 T2 中命中 -> 移至 T2 MRU 端（无自适应调整）

CaseI(x) ==
  /\ In(T1, x) \/ In(T2, x)
  /\ T1' = Remove(T1, x)
  /\ T2' = <<x>> \o Remove(T2, x)
  /\ UNCHANGED <<B1, B2, p>>

\* CASE II: x 在 B1（T1 幽灵）中 -> 增加 p，x 进 T2 MRU；满则先驱逐
\* 论文公式: p = min(p + max(|B2|/|B1|, 1), c)

CaseII(x) ==
  /\ ~In(T1, x) /\ ~In(T2, x)
  /\ In(B1, x)
  /\ LET pNew  == Min2(p + Max2(Len(B2) \div Max2(Len(B1), 1), 1), Capacity)
         ev    == IF TotalCache = Capacity THEN Evict(x) ELSE <<T1, T2, B1, B2>>
         newT1 == ev[1]
         newT2 == ev[2]
         newB1 == ev[3]
         newB2 == ev[4]
     IN /\ p  ' = pNew
        /\ T1' = newT1
        /\ T2' = <<x>> \o Remove(newT2, x)
        /\ B1' = Remove(newB1, x)
        /\ B2' = newB2

\* CASE III: x 在 B2（T2 幽灵）中 -> 减少 p，x 进 T2 MRU；满则先驱逐
\* 论文公式: p = max(p - max(|B1|/|B2|, 1), 0)

CaseIII(x) ==
  /\ ~In(T1, x) /\ ~In(T2, x)
  /\ In(B2, x)
  /\ LET pNew  == Max2(p - Max2(Len(B1) \div Max2(Len(B2), 1), 1), 0)
         ev    == IF TotalCache = Capacity THEN Evict(x) ELSE <<T1, T2, B1, B2>>
         newT1 == ev[1]
         newT2 == ev[2]
         newB1 == ev[3]
         newB2 == ev[4]
     IN /\ p  ' = pNew
        /\ T1' = newT1
        /\ T2' = <<x>> \o Remove(newT2, x)
        /\ B1' = newB1
        /\ B2' = Remove(newB2, x)

\* CASE IV: 完全 miss -> x 进 T1 MRU
\* 处理顺序（依论文 4.3 节）：
\*   1. 若缓存满，执行 REPLACE 类驱逐
\*   2. 若 |T1|+|B1| = c（L1 满），从 B1 尾丢弃幽灵
\*   3. 若 |T2|+|B2| = c（L2 满），从 B2 尾丢弃幽灵
\* 注：TLA+ LET 为单层并行绑定，分层 LET 实现链式更新
CaseIV(x) ==
  /\ ~In(T1, x) /\ ~In(T2, x) /\ ~In(B1, x) /\ ~In(B2, x)
  /\ LET ev == IF TotalCache = Capacity THEN Evict(x) ELSE <<T1, T2, B1, B2>>
     IN LET newT1 == ev[1]
            newT2 == ev[2]
            newB1 == ev[3]
            newB2 == ev[4]
        IN LET b1New == IF Len(newT1) + Len(newB1) = Capacity
                        THEN Remove(newB1, newB1[Len(newB1)])
                        ELSE newB1
           IN /\ p  ' = p
              /\ T1' = <<x>> \o newT1
              /\ T2' = newT2
              /\ B1' = b1New
              /\ B2' = IF Len(newT2) + Len(newB2) = 2 * Capacity
                       THEN Remove(newB2, newB2[Len(newB2)])
                       ELSE newB2

Next == \E x \in Keys: CaseI(x) \/ CaseII(x) \/ CaseIII(x) \/ CaseIV(x)

Spec ==
  /\ Init
  /\ [][Next]_vars
  /\ WF_vars(Next)

-----------------------------------------------------------------------------
\* 不变式

ArcCapacityInv == Len(T1) + Len(T2) <= Capacity

GhostBoundInv ==
  /\ Len(T1) + Len(B1) <= Capacity
  /\ Len(T2) + Len(B2) <= 2 * Capacity

DisjointInv ==
  /\ \A a \in DOMAIN T1: ~In(T2, T1[a]) /\ ~In(B1, T1[a]) /\ ~In(B2, T1[a])
  /\ \A a \in DOMAIN T2: ~In(B1, T2[a]) /\ ~In(B2, T2[a])
  /\ \A a \in DOMAIN B1: ~In(B2, B1[a])

=============================================================================
