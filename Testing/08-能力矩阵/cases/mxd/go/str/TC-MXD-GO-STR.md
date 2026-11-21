# TC-MXD-GO-STR Go stdlib RESP 客户端冒烟

- **用例ID**：TC-MXD-GO-STR | **优先级**：P1 | **矩阵格**：MX-D / GO / STR
- **自动化**：L2 资产型（go run 直跑） | **种子**：M2+ 补批 2026-11-21（○E→●：客户端资产由主控编写落地）
- **运行时**：ANY + Go 工具链（宿主已装）+ lab redis（DOCKER+PODMAN）
- **目的**：Go 语言维从"文档示例"落到可执行冒烟：stdlib RESP 客户端对 lab redis 完成 SET/GET/DEL/GET-after-DEL 四断言（**刻意无 go-redis 依赖**——规避模块拉取网络风险，语言维验证的是协议面非 SDK 面）
- **关联**：`cases/mxd/go/str/main.go` / docs 03.01 数据结构章

## 前置条件

- lab redis 在跑（podman：redis-bench-lab 或哨兵栈主节点，密码 lab-password，宿主端口可达）
- go 工具链（`go version`）

## 步骤（GWT 五段式）

```bash
# Given redis 在跑于 127.0.0.1:6379（密码 lab-password）
# When go run 冒烟客户端
cd Testing/08-能力矩阵/cases/mxd/go/str && go run main.go -addr 127.0.0.1:6379 -pass lab-password
# Then 四断言 PASS（+OK / v1 / :1 / (nil)），末行 GO-STR-SMOKE-PASS，RC=0
```

## 实测断言（enrich 批 2026-11-21）

- **执行资产**：`cases/mxd/go/str/main.go`——stdlib RESP 客户端（零外部依赖），步骤规格=[期望,命令,参数...]（{K}=每族唯一键）
- **断言序列**：SET→+OK / GET→v1 / DEL→:1 / GET→(nil)（唯一键 runid 隔离）
- **判定**：全步骤期望匹配=PASS；任一失配=FAIL（输出 got/want 对）

## 预期结果

- 4×PASS + GO-STR-SMOKE-PASS

## 通过标准

RC=0；CONNECT_FAIL=容器未起或端口未映射（先按容器适配规范 §1 核对运行时）；AUTH_FAIL=密码漂移。

## 失败纠正与修正指引

1. 协议解析 fail：RESP 简化解析只支持本用例四命令语义，扩命令时需升级解析器。
2. 本格只证语言维协议面；SDK 面（go-redis）单测属 M3 扩展位。
