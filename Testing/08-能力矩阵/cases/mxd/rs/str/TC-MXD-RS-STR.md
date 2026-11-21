# TC-MXD-RS-STR Rust std RESP 客户端冒烟

- **用例ID**：TC-MXD-RS-STR | **优先级**：P1 | **矩阵格**：MX-D / RS / STR
- **自动化**：L2 资产型（cargo run 直跑） | **种子**：M2+ 补批 2026-11-21（○E→●）
- **运行时**：ANY + Rust 工具链（宿主已装）+ lab redis（DOCKER+PODMAN）
- **目的**：Rust 语言维可执行冒烟：std TcpStream RESP 客户端四断言（**零 crates 依赖**——cargo new 后单文件即可跑，规避 crates.io 拉取风险）
- **关联**：`cases/mxd/rs/str/main.rs`（cargo 工程骨架由 hermes 首跑时 `cargo init` 补建或直接 rustc 直编：`rustc main.rs -o smoke && ./smoke --addr ... --pass ...`）/ docs 03.01

## 前置条件

- lab redis 在跑（密码 lab-password）
- rustc（`rustc --version`）

## 步骤（GWT 五段式）

```bash
# Given redis 在跑于 127.0.0.1:6379
# When 直编直跑冒烟客户端
cd Testing/08-能力矩阵/cases/mxd/rs/str && rustc main.rs -o str_smoke && ./str_smoke --addr 127.0.0.1:6379 --pass lab-password
# Then 四断言 PASS，RC=0
```

## 实测断言（enrich 批 2026-11-21）

- **执行资产**：`cases/mxd/rs/str/main.rs`——stdlib RESP 客户端（零外部依赖），步骤规格=[期望,命令,参数...]（{K}=每族唯一键）
- **断言序列**：SET→+OK / GET→v1 / DEL→:1 / GET→(nil)（唯一键 runid 隔离）
- **判定**：全步骤期望匹配=PASS；任一失配=FAIL（输出 got/want 对）

## 预期结果

- SET +OK / GET v1 / DEL :1 / GET-after-DEL (nil)

## 通过标准

RC=0。边界声明：与 GO 格同理——本格证协议面；redis-rs SDK 面属 M3 扩展位。

## 失败纠正与修正指引

1. rustc 缺：装 rustup（hermes 环境批）；本资产刻意单文件无工程依赖。
2. 解析 fail 处理同 GO 格。
