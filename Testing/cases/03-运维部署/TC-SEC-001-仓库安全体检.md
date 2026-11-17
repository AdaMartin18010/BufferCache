# TC-SEC-001 仓库安全体检

- **用例ID**：TC-SEC-001 | **优先级**：P1 | **自动化**：self_verify 已覆盖（`security` 子命令，含于 `all`）
- **目的**：三合一常态体检——① 跟踪文件机密模式扫描（密钥/口令/token/私钥/AWS Key）② 大文件检查（>10MB）③ 本地 Redis 未授权访问探测（C7 动态安全的最小落地）
- **关联**：[04.02 缓存安全](../../docs/04-架构设计/04.02-缓存安全/README.md)；requirements.txt（依赖锁定）

## 步骤

```bash
python Testing/self_verify.py security
# 静态项：git ls-files 全量文本扫描（archive 与二进制豁免；占位符 ${}/<>/xxx 不误报）
# 动态项：socket 探测 127.0.0.1:6379，PONG 即未授权暴露（NOAUTH 为正常）
```

## 预期结果

- 机密扫描 0 命中（2026-11-17 基线：跟踪文件全绿）
- 大文件 0 个（仓库 1.5MiB 健康）
- 无本地实例时动态项提示跳过；有实例时必须 NOAUTH（需认证）

## 失败纠正与修正指引

1. 疑似密钥命中：先确认是否占位符误报（补充 PLACEHOLDER_OK 模式）；真实泄漏→**轮换密钥**（历史已入库的改文件无意义），再评估是否清历史。
2. 未授权暴露：立即 `requirepass` + 绑定内网 + 防火墙；复测转绿后登记。
3. 大文件：评估是否该走 Git LFS 或移出仓库。
4. 修正：新机密模式（如新 token 格式）加入 SECRET_PAT；本用例失败即阻断提交。

## 依赖锁定说明

本项目运行时依赖仅 requests + PyYAML，已于 requirements.txt 锁定版本（2026-11-17）；依赖 CVE 扫描建议在 CI 中加 `pip-audit` 步骤（本机未装时由 CI 覆盖）。
