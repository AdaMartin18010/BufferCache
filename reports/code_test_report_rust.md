# BufferCache 项目代码测试报告

**生成时间**: 2026-11-17 11:20:33

## 测试统计

- **总代码块数**: 8
- **测试通过**: 5
- **测试失败**: 2
- **跳过（环境依赖/上下文片段）**: 1
- **可运行代码通过率**: 71.4%（通过/(通过+失败)，不含跳过）

## 详细结果

### docs\02-系统实现\02.06-程序设计实践\02.06.01-容错机制设计.md

- ✅ 行 1089-1188 (rust): 测试通过
- ✅ 行 1193-1274 (rust): 测试通过

### docs\02-系统实现\02.06-程序设计实践\02.06.02-异常处理模式.md

- ⏭️ 行 786-874 (rust): 跳过：包含占位符或TODO
- ❌ 行 879-938 (rust): 编译失败: error[E0599]: no variant, associated function, or constant named `new` found for enum `CacheError` in the current scope
  --> C:\Users\luyan\AppData\Local\Temp\tmptrmyh_hv\main.rs:30:32
   |
 4 | enum CacheError {
   | --------------- variant, associated function, or constant `new` not found for thi

### docs\02-系统实现\02.06-程序设计实践\02.06.03-程序设计示例.md

- ✅ 行 736-854 (rust): 测试通过
- ✅ 行 1238-1363 (rust): 测试通过

### docs\02-系统实现\02.06-程序设计实践\02.06.04-全局系统容错.md

- ✅ 行 1055-1191 (rust): 测试通过

### docs\07-运维与部署\07.07-自动化运维\07.07.02-自动化运维脚本.md

- ❌ 行 1251-1350 (rust): 编译失败: warning: unused import: `std::path::Path`
 --> C:\Users\luyan\AppData\Local\Temp\tmphev55nfz\main.rs:3:5
  |
3 | use std::path::Path;
  |     ^^^^^^^^^^^^^^^
  |
  = note: `#[warn(unused_imports)]` (part of `#[warn(unused)]`) on by default

error[E0433]: cannot find module or crate `libc` in this sc
