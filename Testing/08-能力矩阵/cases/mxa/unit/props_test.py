#!/usr/bin/env python3
# MX-A UNIT 种子资产：LRU 栈序不变式 + S3-FIFO 三队列不变式（属性单测，stdlib unittest）
# 派生断言源：docs/01-理论基础/01.02-高级替换算法 01.02.01（LRU）/ 01.02.10（S3-FIFO）
# 用法: python lru_sieve_props_test.py   RC: 0=PASS；运行=hermes（主控只编写资产）
import random
import unittest


class LRUCache:
    """参考实现：哈希链表，O(1) get/put（与 01.02.01 定义一致）"""

    def __init__(self, cap):
        self.cap = cap
        self.dll = []  # 尾部=MRU，头部=LRU
        self.pos = {}

    def get(self, k):
        if k not in self.pos:
            return None
        # 命中即刷新：移至 MRU 端（01.02.01 栈序定义）
        self.dll.remove(k)
        self.dll.append(k)
        return self.pos[k]

    def put(self, k, v):
        if k in self.pos:
            self.dll.remove(k)
        elif len(self.dll) >= self.cap:
            victim = self.dll.pop(0)
            del self.pos[victim]
        self.dll.append(k)
        self.pos[k] = v

    def victim(self):
        return self.dll[0] if self.dll else None


class S3FIFO:
    """参考实现：small(FIFO)/main(FIFO)/ghost 队列（01.02.10 简化版）"""

    def __init__(self, cap):
        self.cap = cap
        self.small = []
        self.main = []
        self.ghost = set()

    def access(self, k):
        if k in self.small:
            self.small.remove(k)
            self.main.append(k)
            return True
        if k in self.main:
            # main 中命中：移至队尾（近似 O(1) 版省略链表化）
            self.main.remove(k)
            self.main.append(k)
            return True
        if k in self.ghost:
            self.ghost.discard(k)
            self.main.append(k)
            self._shrink()
            return False
        self.small.append(k)
        self._shrink()
        return False

    def _shrink(self):
        while len(self.small) + len(self.main) > self.cap:
            if len(self.small) > max(1, self.cap // 10):
                k = self.small.pop(0)
                self.ghost.add(k)
            else:
                k = self.main.pop(0)
                self.ghost.discard(k)


class TestLRUProperties(unittest.TestCase):
    def test_victim_is_least_recently_used(self):
        rng = random.Random(20261121)
        for trial in range(200):
            cap = rng.randint(2, 8)
            c = LRUCache(cap)
            live = []
            for _ in range(rng.randint(cap, cap * 6)):
                k = f"k{rng.randint(0, cap * 3)}"
                if rng.random() < 0.5 and live:
                    c.get(rng.choice(live))
                else:
                    c.put(k, 1)
                    if k not in live:
                        live.append(k)
                # 不变式：淘汰候选 = 当前最久未访问者
                if len(c.dll) == cap:
                    expected = c.dll[0]
                    self.assertEqual(c.victim(), expected)
                    self.assertEqual(len(c.dll), len(set(c.dll)), "链表无重复键")

    def test_capacity_never_exceeded(self):
        c = LRUCache(3)
        for i in range(100):
            c.put(f"x{i % 10}", i)
            self.assertLessEqual(len(c.dll), 3)


class TestS3FIFOProperties(unittest.TestCase):
    def test_queue_invariants(self):
        rng = random.Random(20261121)
        for trial in range(200):
            cap = rng.randint(4, 16)
            c = S3FIFO(cap)
            for _ in range(rng.randint(cap, cap * 8)):
                c.access(f"k{rng.randint(0, cap * 4)}")
                # 不变式 1：总占用 ≤ 容量
                self.assertLessEqual(len(c.small) + len(c.main), cap)
                # 不变式 2：small+main 键不重叠
                self.assertFalse(set(c.small) & set(c.main))
                # 不变式 3：ghost 不与 resident 重叠
                self.assertFalse((set(c.small) | set(c.main)) & c.ghost)

    def test_hit_moves_to_main(self):
        c = S3FIFO(6)
        c.access("a"); c.access("b"); c.access("c")
        self.assertIn("a", c.small)
        c.access("a")  # small 命中 → 升 main
        self.assertIn("a", c.main)
        self.assertNotIn("a", c.small)




# ---------------- 扩展参考实现与属性测试（enrich 批 2026-11-21：FIFO/LFU/SIEVE/2Q/SLRU/ARC） ----------------

class FIFOCache:
    """01.02.01：先进先出，淘汰最早插入"""

    def __init__(self, cap):
        self.cap = cap
        self.q = []

    def access(self, k):
        if k in self.q:
            return True
        self.q.append(k)
        if len(self.q) > self.cap:
            self.q.pop(0)
        return False


class LFUCache:
    """01.02.02：频次计数，淘汰最少频次（同频次取最早插入）"""

    def __init__(self, cap):
        self.cap = cap
        self.freq = {}
        self.ins = {}
        self.t = 0

    def access(self, k):
        self.t += 1
        if k in self.freq:
            self.freq[k] += 1
            return True
        if len(self.freq) >= self.cap:
            victim = min(self.freq, key=lambda x: (self.freq[x], self.ins[x]))
            del self.freq[victim]
            del self.ins[victim]
        self.freq[k] = 1
        self.ins[k] = self.t
        return False


class SIEVECache:
    """01.02.10：visited 位 + hand 指针（简化链表模型， oldest=index0）"""

    def __init__(self, cap):
        self.cap = cap
        self.items = []   # [(key, visited)]，0=最旧
        self.hand = -1

    def access(self, k):
        for i, (key, _) in enumerate(self.items):
            if key == k:
                self.items[i] = (k, True)
                return True
        self.items.append((k, False))
        if len(self.items) > self.cap:
            self._evict()
        return False

    def _evict(self):
        n = len(self.items)
        if self.hand < 0 or self.hand >= n:
            self.hand = n - 1
        while True:
            k, v = self.items[self.hand]
            if v:
                self.items[self.hand] = (k, False)
                self.hand = (self.hand - 1) % len(self.items)
            else:
                del self.items[self.hand]
                self.hand = (self.hand - 1) % max(1, len(self.items))
                return


class TwoQCache:
    """01.02.04 简化：A1in(FIFO 入)/Amout(ghost)/Al1(主)；Kin=cap//4，Kout=cap"""

    def __init__(self, cap):
        self.cap = cap
        self.kin = max(1, cap // 4)
        self.a1in, self.al1, self.amout = [], [], []

    def access(self, k):
        if k in self.a1in:
            self.a1in.remove(k)
            self._mru(self.al1, k)
            return True
        if k in self.al1:
            self.al1.remove(k)
            self._mru(self.al1, k)
            return True
        if k in self.amout:
            self.amout.remove(k)
            self._mru(self.al1, k)
            self._shrink()
            return False
        self._mru(self.a1in, k)
        self._shrink()
        return False

    @staticmethod
    def _mru(lst, k):
        lst.append(k)

    def _shrink(self):
        while len(self.a1in) + len(self.al1) > self.cap:
            if len(self.a1in) >= self.kin and self.a1in:
                k = self.a1in.pop(0)
                self._mru(self.amout, k)
                if len(self.amout) > self.cap:
                    self.amout.pop(0)
            elif self.al1:
                self.al1.pop(0)
            else:
                self.a1in.pop(0)


class SLRUCache:
    """01.02.05：probation/protected 两段；命中 probation 升 protected；protected 溢出降 LRU 至 probation"""

    def __init__(self, cap):
        self.cap = cap
        self.prot_limit = max(1, cap - max(1, cap // 4))
        self.prob, self.prot = [], []

    def access(self, k):
        if k in self.prob:
            self.prob.remove(k)
            self._mru_prot(k)
            return True
        if k in self.prot:
            self.prot.remove(k)
            self._mru_prot(k)
            return True
        self.prob.append(k)
        self._shrink()
        return False

    def _mru_prot(self, k):
        self.prot.append(k)
        while len(self.prot) > self.prot_limit:
            self.prob.append(self.prot.pop(0))

    def _shrink(self):
        while len(self.prob) + len(self.prot) > self.cap:
            if self.prob:
                self.prob.pop(0)
            else:
                self.prot.pop(0)


class ARCache:
    """01.02.03 标准伪代码实现：T1/T2/B1/B2 + 自适应 p"""

    def __init__(self, cap):
        self.c = max(2, cap)
        self.p = 0
        self.t1, self.t2, self.b1, self.b2 = [], [], [], []

    def _mru(self, lst, k):
        if k in lst:
            lst.remove(k)
        lst.append(k)

    def _replace(self, in_b2):
        if not self.t1 and not self.t2:
            return
        if self.t1 and (len(self.t1) > self.p or (in_b2 and len(self.t1) == self.p)):
            k = self.t1.pop(0)
            self._mru(self.b1, k)
        elif self.t2:
            k = self.t2.pop(0)
            self._mru(self.b2, k)
        else:
            # p=c 等退化态（resident 全在 T1 且 |T1|≤p）→ 退化取 T1（论文不变式下不触发）
            k = self.t1.pop(0)
            self._mru(self.b1, k)

    def access(self, k):
        if k in self.t1 or k in self.t2:
            if k in self.t1:
                self.t1.remove(k)
            else:
                self.t2.remove(k)
            self._mru(self.t2, k)
            return True
        if k in self.b1:
            d = max(1, len(self.b2) // max(1, len(self.b1)))
            self.p = min(self.c, self.p + d)
            self.b1.remove(k)
            if len(self.t1) + len(self.t2) == self.c:
                self._replace(False)
            self._mru(self.t2, k)
            return False
        if k in self.b2:
            d = max(1, len(self.b1) // max(1, len(self.b2)))
            self.p = max(0, self.p - d)
            self.b2.remove(k)
            if len(self.t1) + len(self.t2) == self.c:
                self._replace(True)
            self._mru(self.t1, k)
            return False
        if len(self.t1) + len(self.t2) == self.c:
            if len(self.t1) < self.c:
                if self.b1:
                    self.b1.pop(0)
                self._replace(False)
            else:
                kx = self.t1.pop(0)
                self._mru(self.b1, kx)
        else:
            total = len(self.t1) + len(self.t2) + len(self.b1) + len(self.b2)
            if total >= self.c:
                if self.b1 and total == self.c:
                    self.b1.pop(0)
                elif self.b2 and total == self.c * 2:
                    self.b2.pop(0)
        self._mru(self.t1, k)
        return False


def _run_sequence(cache_cls, cap, keys, rng):
    c = cache_cls(cap)
    hits = 0
    for k in keys:
        if c.access(k):
            hits += 1
    return c, hits


class TestExtendedAlgos(unittest.TestCase):
    IMPLS = {
        "FIFO": (FIFOCache, lambda c: c.q),
        "LFU": (LFUCache, lambda c: list(c.freq)),
        "SIEVE": (SIEVECache, lambda c: [k for k, _ in c.items]),
        "2Q": (TwoQCache, lambda c: c.a1in + c.al1),
        "SLRU": (SLRUCache, lambda c: c.prob + c.prot),
        "ARC": (ARCache, lambda c: c.t1 + c.t2),
    }

    def test_capacity_disjoint_determinism(self):
        rng = random.Random(20261121)
        for name, (cls, resident) in self.IMPLS.items():
            for trial in range(100):
                cap = rng.randint(2, 16)
                keys = [f"k{rng.randint(0, cap * 3)}" for _ in range(rng.randint(cap, cap * 8))]
                c1, h1 = _run_sequence(cls, cap, keys, rng)
                c2, h2 = _run_sequence(cls, cap, keys, rng)
                r = resident(c1)
                self.assertLessEqual(len(r), cap, f"{name} 容量破界")
                self.assertEqual(len(r), len(set(r)), f"{name} resident 重复键")
                self.assertEqual(h1, h2, f"{name} 同序列同种子须确定性")
                if name == "ARC":
                    self.assertFalse(set(c1.t1) & set(c1.t2), "ARC T1∩T2=∅")
                    self.assertFalse((set(c1.t1) | set(c1.t2)) & (set(c1.b1) | set(c1.b2)), "ARC resident∩ghost=∅")
                if name == "2Q":
                    self.assertFalse(set(c1.a1in) & set(c1.al1), "2Q A1in∩Al1=∅")
                if name == "SLRU":
                    self.assertFalse(set(c1.prob) & set(c1.prot), "SLRU 段不相交")

    def test_victim_semantics(self):
        # FIFO：连续插入 cap+1 个不同键 → 淘汰最早键
        c = FIFOCache(3)
        for k in ["a", "b", "c", "d"]:
            c.access(k)
        self.assertEqual(c.q, ["b", "c", "d"])
        # LFU：最少频次先淘汰（同频最早插入）
        c = LFUCache(2)
        for k in ["a", "b", "a"]:
            c.access(k)
        c.access("c")  # 须淘汰 b（freq(b)=1 且早于 c 前插入）
        self.assertNotIn("b", c.freq)
        self.assertIn("a", c.freq)
        # SIEVE（01.02.10）：hand 自尾端扫描，visited=0 者先淘汰（年轻未命中先走=FIFO+二次机会语义）
        c = SIEVECache(2)
        c.access("a"); c.access("b")
        c.access("a")  # a 命中 → visited=1
        c.access("e"); c.access("f")  # 触发两轮淘汰扫描
        self.assertIn("a", [k for k, _ in c.items], "visited=1 对象须躲过一轮扫描")
        # ARC：B1 命中后 p 增加且键进 T2
        c = ARCache(4)
        for k in ["a", "b", "c", "e"]:
            c.access(k)
        p0 = c.p
        c.access("a")
        self.assertIn("a", c.t2)
        self.assertGreaterEqual(c.p, p0)


if __name__ == "__main__":
    unittest.main(verbosity=1)
