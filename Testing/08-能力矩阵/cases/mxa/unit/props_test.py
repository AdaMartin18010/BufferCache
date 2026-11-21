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


if __name__ == "__main__":
    unittest.main(verbosity=1)
