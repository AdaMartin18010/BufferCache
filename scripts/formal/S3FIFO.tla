---- MODULE S3FIFO ----
(*
 * S3-FIFO 缓存替换算法的 TLA+ 形式化规约（SOSP 2023, Yang et al.）
 * 对应文档: docs/01-理论基础/01.02-高级替换算法/01.02.10-S3-FIFO与SIEVE算法.md
 *
 * 简化模型（幽灵队列省略，不影响 miss-ratio 主结论——01.02.10 注明）：
 *   S 段（准入，约 10% 容量）+ M 段（受保护，90%），每对象 2bit 频率计数 0-3。
 *   - 命中：S 或 M 中 freq+1（上限 3）
 *   - miss 未满：入 S 尾（freq=0）
 *   - miss 满：S 满则从 S 头驱逐——freq>0 晋升 M（M 满则从 M 头循环
 *     驱逐 freq<3 者，freq=3 者减 1 二次机会）；freq=0 直接淘汰
 *
 * 验证目标（safety）:
 *   1. CapacityInv   —— |S|+|M| <= Capacity
 *   2. DisjointInv   —— S 与 M 无交集（对象不重复驻留）
 *   3. FreqRange     —— 所有计数在 0-3
 * 验证目标（liveness，强公平性）:
 *   1. AllKeysEventuallyCached
 *
 * 运行: java -jar tla2tools.jar -config S3FIFO.cfg S3FIFO.tla
 *)

EXTENDS Naturals, Sequences, FiniteSets

CONSTANTS Keys, Capacity

VARIABLES S,           \* S 段：key -> freq（0-3），序列序即 FIFO 序（Head=最老）
          M            \* M 段：key -> freq（0-3）


Min2(a, b) == IF a < b THEN a ELSE b

Max2(a, b) == IF a > b THEN a ELSE b

vars == <<S, M>>

SCap == Max2(1, Capacity \div 10)

MCap == Capacity - SCap


\* 从函数（key->freq）域中取最老 key（Sequences 不便，用函数+选序辅助）
\* 规约中以"域的某个枚举序"表示 FIFO 序——为可模型检查，用函数+有序结构：
\* 改为序列存储：seq of <<key, freq>>

SKeys == {S[i][1] : i \in DOMAIN S}

MKeys == {M[i][1] : i \in DOMAIN M}

RECURSIVE SetFreq(_, _, _)
SetFreq(seq, k, f) ==
  IF seq = <<>> THEN <<>>
  ELSE IF Head(seq)[1] = k THEN <<<<k, f>>>> \o Tail(seq)
  ELSE <<Head(seq)>> \o SetFreq(Tail(seq), k, f)

GetFreq(seq, k) == Head(SelectSeq(seq, LAMBDA x: x[1] = k))[2]

RemoveKey(seq, k) == SelectSeq(seq, LAMBDA x: x[1] # k)

\* M 段循环驱逐：从头扫描，freq<3 淘汰；=3 减 1 后置尾（二次机会）
RECURSIVE MEvictScan(_)
MEvictScan(m) ==
  IF m = <<>> THEN m
  ELSE LET h == Head(m)
       IN IF h[2] < 3 THEN RemoveKey(m, h[1])
          ELSE MEvictScan(Append(Tail(m), <<h[1], h[2] - 1>>))
          \* 全 3 场景：减 1 置尾后递归，至多 3 轮必淘汰（值严格递减）

MEvict(m) == IF m = <<>> THEN m ELSE MEvictScan(m)

Init ==
  /\ S = <<>>
  /\ M = <<>>

Hit(k) ==
  /\ (k \in SKeys) \/ (k \in MKeys)
  /\ IF k \in SKeys
     THEN S' = SetFreq(S, k, Min2(3, GetFreq(S, k) + 1))
     ELSE S' = S
  /\ IF k \in MKeys
     THEN M' = SetFreq(M, k, Min2(3, GetFreq(M, k) + 1))
     ELSE M' = M


Miss(k) ==
  /\ k \notin SKeys /\ k \notin MKeys
  /\ LET sFull == Len(S) >= SCap
     IN IF sFull
        THEN LET victim == Head(S)
                 sRest == Tail(S)
             IN IF victim[2] > 0
                THEN \* 晋升 M；M 满则驱逐
                   LET m1 == IF Len(M) >= MCap THEN MEvict(M) ELSE M
                   IN /\ M' = Append(m1, <<victim[1], victim[2]>>)
                      /\ S' = Append(sRest, <<k, 0>>)
                ELSE \* freq=0 直接淘汰
                   /\ S' = Append(sRest, <<k, 0>>)
                      /\ M' = M
        ELSE /\ S' = Append(S, <<k, 0>>)
             /\ M' = M

PerKey(k) == Hit(k) \/ Miss(k)

Next == \E k \in Keys: PerKey(k)

Spec ==
  /\ Init
  /\ [][Next]_vars
  /\ \A k \in Keys: SF_vars(PerKey(k))

CapacityInv == Len(S) + Len(M) <= Capacity

DisjointInv == (SKeys \cap MKeys) = {}

FreqRange ==
  /\ \A i \in DOMAIN S: S[i][2] \in 0..3
  /\ \A i \in DOMAIN M: M[i][2] \in 0..3

AllKeysEventuallyCached == \A k \in Keys: []<>(k \in SKeys \/ k \in MKeys)

=============================================================================

=============================================================================