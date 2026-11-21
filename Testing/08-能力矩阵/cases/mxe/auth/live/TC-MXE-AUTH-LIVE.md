# TC-MXE-AUTH-LIVE 认证实载验证（requirepass/ACL）

- **用例ID**：TC-MXE-AUTH-LIVE | **优先级**：P1 | **矩阵格**：MX-E / AUTH / LIVE
- **自动化**：L2 剧本型（hermes 执行回填） | **种子**：M2 人工精修 2026-11-21
- **运行时**：DOCKER+PODMAN（redis 容器即可；基准形态 docker exec，podman 按适配规范 §2 替换）
- **目的**：04.02 缓存安全的认证配置从纸面落到实载：requirepass 生效、未授权拒绝、ACL 用户最小权限
- **关联**：MX-E 维度定义 `MX-E-domains.tsv` AUTH 行 / docs/04-架构设计/04.02-缓存安全 / 既有静态面 TC-OPS-003（本格补 LIVE 面）

## 前置条件

- redis 容器在跑（redis-lab 任意形态；密码 lab-password）
- 运行时探测完成（适配规范 §1），命令已按 §2 适配（下文以 docker 为基准形）

## 步骤（GWT 五段式）

```bash
# Given redis 容器在跑且已配置 requirepass lab-password
# When 未带密码执行受保护命令
docker exec <c> redis-cli SET k1 v1
# Then 返回 NOAUTH Authentication required（未授权拒绝断言）
docker exec <c> redis-cli -a lab-password --no-auth-warning SET k1 v1   # 带密码成功

# When 创建最小权限 ACL 用户（只读）
docker exec <c> redis-cli -a lab-password --no-auth-warning ACL SETUSER readonly on '>ro123' '+GET' '~*'
# Then 该用户 GET 成功
docker exec <c> redis-cli --user readonly --pass ro123 --no-auth-warning GET k1
# And 该用户 SET 被拒绝（NOPERM 断言）
docker exec <c> redis-cli --user readonly --pass ro123 --no-auth-warning SET k2 v2 || echo "NOPERM-as-expected"
```

## 预期结果

- 无密码访问被拒（NOAUTH）；正确密码成功
- ACL 只读用户 GET 成功 / SET 返回 NOPERM

## 通过标准

三条断言全部成立；失败时先核对 redis.conf 的 requirepass/aclfile 是否与 04.02 推荐配置一致（修正指引：配置漂移→回写 docs；容器未配密码→重建 lab 环境）。

## 失败纠正与修正指引

1. NOAUTH 未出现：实例未开认证——lab compose 已带 requirepass，若被改回写 fixtures。
2. ACL NOPERM 未出现：ACL 规则写错——`ACL GETUSER readonly` 输出核对 +rules。
3. 修正：本用例实测结论回填 04.02 安全篇"实载验证"注记。
