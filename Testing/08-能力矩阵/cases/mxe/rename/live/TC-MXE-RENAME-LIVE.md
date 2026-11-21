# TC-MXE-RENAME-LIVE 危险命令重命名实载验证

- **用例ID**：TC-MXE-RENAME-LIVE | **优先级**：P1 | **矩阵格**：MX-E / RENAME / LIVE
- **自动化**：L2 剧本型（hermes 执行回填） | **种子**：M2 人工精修 2026-11-21
- **运行时**：DOCKER+PODMAN
- **目的**：CONFIG SET rename-command 实载生效：被重命名命令原入口拒绝、新入口可用；验证 04.02 推荐重命名集（FLUSHALL/FLUSHDB/KEYS/CONFIG 等）
- **关联**：MX-E 维度定义 RENAME 行 / docs/04-架构设计/04.02-缓存安全 / 既有静态面 TC-OPS-003

## 前置条件

- redis 容器在跑（密码 lab-password）；允许 CONFIG SET（未禁用 CONFIG 本身）

## 步骤（GWT 五段式）

```bash
# Given 容器初始态（FLUSHALL 原名可用）
# When 运行时重命名 FLUSHALL 为 ""（禁用）并重命名 KEYS 为 KEYS_HIDDEN
docker exec <c> redis-cli -a lab-password --no-auth-warning CONFIG SET rename-command FLUSHALL ""
docker exec <c> redis-cli -a lab-password --no-auth-warning CONFIG SET rename-command KEYS KEYS_HIDDEN
# Then 原入口被拒绝（ERR unknown command 断言）
docker exec <c> redis-cli -a lab-password --no-auth-warning FLUSHALL || echo "blocked-as-expected"
docker exec <c> redis-cli -a lab-password --no-auth-warning KEYS '*' || echo "blocked-as-expected"
# And 新入口可用
docker exec <c> redis-cli -a lab-password --no-auth-warning KEYS_HIDDEN '*'
# And 重启后持久性（rename-command 为启动配置项，运行时 CONFIG SET 不落盘——断言仅运行时生效并注明）
# 恢复：CONFIG SET 无逆操作，重建容器即可还原
```

## 预期结果

- 被禁/改名命令原入口返回 unknown command；新入口行为正常

## 通过标准

四条断言成立；**边界声明**：rename-command 仅启动配置持久，运行时 CONFIG SET 验证的是机制语义，生产持久化须在 redis.conf 层验证（04.02 已述，不重复展开）。

## 失败纠正与修正指引

1. CONFIG SET rename-command 报错：实例以命令行方式已重名——核对启动参数。
2. 修正：实测结论回填 04.02 重命名节；新增推荐重命名命令时同步本用例步骤。
