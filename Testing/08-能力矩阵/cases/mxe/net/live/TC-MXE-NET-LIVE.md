# TC-MXE-NET-LIVE 网络面实载验证（bind/protected-mode）

- **用例ID**：TC-MXE-NET-LIVE | **优先级**：P1 | **矩阵格**：MX-E / NET / LIVE
- **自动化**：L2 剧本型 | **种子**：M2+ 补批 2026-11-21（○E→●）
- **运行时**：DOCKER+PODMAN
- **目的**：04.02 网络隔离配置实载：bind 127.0.0.1 时容器间/外部连接被拒、protected-mode yes + 无密码时远程拒绝——两条红旗配置的行为断言
- **关联**：MX-E 维度定义 NET 行 / docs/04-架构设计/04.02-缓存安全 / 既有静态面 TC-OPS-003

## 前置条件

- podman 可用；redis:7-alpine 在盘

## 步骤（GWT 五段式）

```bash
# Given 实例 A：bind 127.0.0.1 + requirepass（仅回环）
podman run -d --name net-bind-test -p 6379:6379 redis:7-alpine redis-server --bind 127.0.0.1 --requirepass lab-password
# When 从宿主机连接宿主映射端口（经端口转发进容器回环）
redis-cli -h 127.0.0.1 -p 6379 -a lab-password --no-auth-warning PING
# Then 经宿主转发可达（端口映射在宿主侧），但容器间直连回环绑定不可达：
podman run --rm redis:7-alpine sh -c "redis-cli -h net-bind-test -a lab-password --no-auth-warning PING" || echo "unreachable-as-expected"

# Given 实例 B：protected-mode yes 且无密码
podman run -d --name net-pm-test -p 6382:6379 redis:7-alpine redis-server --protected-mode yes
# When 远程非回环连接尝试
podman run --rm redis:7-alpine sh -c "redis-cli -h host.containers.internal -p 6382 PING" || echo "denied-as-expected"
# Then DENIED Networking（protected-mode 拒绝无密码远程断言）

# 恢复：podman rm -f net-bind-test net-pm-test
```

## 预期结果

- bind 回环：容器间名解析直连失败；宿主转发可达（端口映射语义）
- protected-mode：无密码远程拒绝

## 通过标准

两条拒绝断言成立。**边界声明**：端口映射宿主转发可达≠配置失效——bind 绑定的是容器内监听面，映射由运行时网络层完成，两断言不可混为一谈。

## 失败纠正与修正指引

1. 容器间名解析不通：podman 默认网络 DNS——用 `--network` 显式同网络或 host.containers.internal 兜底。
2. 修正：结论回填 04.02 网络隔离节。
