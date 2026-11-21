# TC-MXA-S3FIFO-UNIT S3-FIFO 三队列不变式属性单测

- **用例ID**：TC-MXA-S3FIFO-UNIT | **优先级**：P1 | **矩阵格**：MX-A / S3FIFO / UNIT
- **自动化**：L1 资产型 | **种子**：M2+ 补批 2026-11-21
- **运行时**：ANY
- **目的**：01.02.10 S3-FIFO 的核心机制落成可回归断言：small/main/ghost 三队列不变式（占用≤容量、resident 无重叠、ghost 与 resident 无重叠、small 命中升 main）
- **关联**：`cases/mxa/unit/props_test.py`（同资产文件，S3FIFO 部分）/ docs 01.02.10

## 前置条件

- python ≥3.8

## 步骤（GWT 五段式）

```bash
# Given 参考实现 S3FIFO（small FIFO / main FIFO / ghost 集合，01.02.10 简化版）
# When 固定种子 200 组随机访问序列（cap 4~16）
python Testing/08-能力矩阵/cases/mxa/unit/props_test.py TestS3FIFOProperties
# Then 不变式 1 占用≤容量；不变式 2 small∩main=∅；不变式 3 ghost∩resident=∅；命中升 main
```

## 预期结果

- `OK`（队列不变式 + 升 main 语义两测试通过）

## 通过标准

退出码 0。**边界声明**：本参考实现为 01.02.10 简化版（main 命中移动未做链表化 O(1)），不变式层面与论文语义等价，性能语义不在本格验证（性能属 MX-C）。

## 失败纠正与修正指引

1. 不变式破：对照 01.02.10 队列进出规则修参考实现。
2. ghost 语义变更须与 01.02.10 同步评审（公式/机制改动走文档变更流程）。
