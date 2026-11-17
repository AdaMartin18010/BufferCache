# BufferCache 项目代码测试报告

**生成时间**: 2026-11-17 11:13:44

## 测试统计

- **总代码块数**: 14
- **测试通过**: 5
- **测试失败**: 6
- **跳过（环境依赖/上下文片段）**: 3
- **可运行代码通过率**: 45.5%（通过/(通过+失败)，不含跳过）

## 详细结果

### docs\00-项目总览\代码示例测试框架.md

- ⏭️ 行 169-190 (go): 跳过：不是完整 main 程序（函数级教学片段）

### docs\02-系统实现\02.06-程序设计实践\02.06.01-容错机制设计.md

- ✅ 行 854-954 (go): 测试通过
- ✅ 行 959-1019 (go): 测试通过
- ✅ 行 1024-1080 (go): 测试通过

### docs\02-系统实现\02.06-程序设计实践\02.06.02-异常处理模式.md

- ⏭️ 行 653-725 (go): 跳过：包含占位符或TODO
- ✅ 行 730-777 (go): 测试通过

### docs\02-系统实现\02.06-程序设计实践\02.06.03-程序设计示例.md

- ❌ 行 598-726 (go): 编译/执行失败: # command-line-arguments
.\main.go:124:9: undefined: fmt

- ❌ 行 1109-1226 (go): 编译/执行失败: # command-line-arguments
.\main.go:98:12: undefined: fmt
.\main.go:101:24: undefined: errors
.\main.go:116:5: undefined: fmt

- ❌ 行 1490-1665 (go): 编译/执行失败: # command-line-arguments
.\main.go:172:5: undefined: fmt
.\main.go:173:5: undefined: fmt
.\main.go:174:5: undefined: fmt


### docs\02-系统实现\02.06-程序设计实践\02.06.04-全局系统容错.md

- ✅ 行 892-1048 (go): 测试通过

### docs\07-运维与部署\07.03-监控告警\07.03.03-告警规则与通知.md

- ⏭️ 行 1275-1288 (go): 跳过：不是完整 main 程序（函数级教学片段）

### docs\07-运维与部署\07.07-自动化运维\07.07.02-自动化运维脚本.md

- ❌ 行 1015-1151 (go): 编译/执行失败: # command-line-arguments
.\main.go:8:5: "strings" imported and not used

- ❌ 行 1156-1241 (go): 编译/执行失败: go: finding module for package github.com/go-redis/redis/v8
go: finding module for package golang.org/x/net/context
go: downloading golang.org/x/net v0.62.0
go: downloading github.com/cespare/xxhash/v2 v2.1.2
# command-line-arguments
.\main.go:46:52: cannot convert "dir" (untyped string constant) to

### docs\08-分布式架构\08.03-分布式协调\08.03.01-分布式锁实践.md

- ❌ 行 418-457 (go): 编译/执行失败: go: finding module for package github.com/go-redsync/redsync/v4
go: finding module for package github.com/go-redsync/redsync/v4/redis/goredis/v8
go: finding module for package github.com/go-redis/redis/v8
go: downloading github.com/go-redis/redis/v8 v8.11.5
go: downloading github.com/go-redsync/reds
