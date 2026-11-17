# TC-OPS-003 缓存安全基线检查

- **用例ID**：TC-OPS-003 | **优先级**：P1 | **自动化**：self_verify 部分覆盖（静态项）；运行时项人工
- **目的**：Redis/缓存部署满足安全基线：认证、绑定、危险命令、补丁、TLS
- **关联**：[04.02](../../../docs/04-架构设计/04.02-缓存安全/README.md)；[07.04.03](../../../docs/07-运维与部署/07.04-故障处理/07.04.03-应急预案.md)

## 步骤（静态，self_verify 覆盖）

```bash
python Testing/self_verify.py ops
# 检查项：
#  1. docs/07 配置示例不得出现 requirepass 硬编码真实口令（只允许 ${VAR}/占位符）
#  2. 示例配置 bind 不得为 0.0.0.0 且无 requirepass 注释说明
#  3. 配置中 rename-command 覆盖 FLUSHALL/CONFIG/EVAL 的示例存在
```

## 步骤（运行时，人工季度执行）

```bash
redis-cli CONFIG GET requirepass     # 非空
redis-cli CONFIG GET bind            # 非全网卡或无防火墙等价物
redis-cli INFO server                # 版本在受支持线内（对照 redis-ecosystem-versions §3）
```

## 预期结果

静态项全过；运行时项四项全过或具备等效补偿控制。

## 失败纠正与修正指引

1. 硬编码口令：改为占位符并引用密钥管理方案；检查 git 历史中的泄漏并轮换。
2. 缺危险命令覆盖：补 rename-command 并验证运维依赖方无脚本破坏。
3. 版本过旧：按 redis-ecosystem-versions 任务 A 升级。
4. 修正：把安全基线表（口令/绑定/TLS/命令/补丁）固化到 07.04.03 附录。
