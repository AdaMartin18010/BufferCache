# BufferCache 项目贡献指南

感谢您对BufferCache项目的关注！本文档将指导您如何为项目做出贡献。

## 📋 目录

- [1. 贡献类型](#1-贡献类型)
- [2. 贡献流程](#2-贡献流程)
- [3. 代码规范](#3-代码规范)
- [4. 文档规范](#4-文档规范)
- [5. 提交规范](#5-提交规范)
- [6. 代码审查](#6-代码审查)

---

## 1. 贡献类型

### 1.1 代码贡献

- **Bug修复**：修复代码中的Bug
- **功能开发**：开发新功能
- **性能优化**：优化代码性能
- **代码重构**：重构代码结构

### 1.2 文档贡献

- **内容补充**：补充文档内容
- **错误修正**：修正文档错误
- **格式优化**：优化文档格式
- **翻译改进**：改进翻译质量

### 1.3 测试贡献

- **单元测试**：编写单元测试
- **集成测试**：编写集成测试
- **性能测试**：编写性能测试
- **文档测试**：测试文档示例

---

## 2. 贡献流程

### 2.1 Fork项目

1. 访问项目GitHub页面
2. 点击"Fork"按钮
3. 克隆Fork的仓库到本地

```bash
git clone https://github.com/your-username/buffercache.git
cd buffercache
```

### 2.2 创建分支

```bash
# 创建特性分支
git checkout -b feature/your-feature-name

# 或创建Bug修复分支
git checkout -b fix/your-bug-fix
```

### 2.3 提交更改

```bash
# 添加更改
git add .

# 提交更改（遵循提交规范）
git commit -m "feat: 添加新功能"

# 推送到Fork的仓库
git push origin feature/your-feature-name
```

### 2.4 创建Pull Request

1. 访问GitHub页面
2. 点击"New Pull Request"
3. 填写PR描述
4. 等待代码审查

---

## 3. 代码规范

### 3.1 代码风格

- **Python**：遵循PEP 8规范
- **JavaScript**：遵循ESLint规范
- **Go**：遵循gofmt规范
- **Java**：遵循Google Java Style Guide

### 3.2 代码注释

```python
def calculate_cache_hit_rate(hits, misses):
    """
    计算缓存命中率

    Args:
        hits: 命中次数
        misses: 未命中次数

    Returns:
        缓存命中率（0-1之间）

    Raises:
        ValueError: 当hits或misses为负数时
    """
    if hits < 0 or misses < 0:
        raise ValueError("hits和misses必须为非负数")

    total = hits + misses
    if total == 0:
        return 0.0

    return hits / total
```

### 3.3 代码测试

- 所有新功能必须包含测试
- 测试覆盖率应达到80%以上
- 使用适当的测试框架

---

## 4. 文档规范

### 4.1 Markdown规范

- 使用标准Markdown语法
- 标题层级清晰
- 代码块指定语言
- 链接使用相对路径

### 4.2 文档结构

每个文档应包含：

1. **目录**：文档目录结构
2. **概述**：文档概述
3. **正文**：主要内容
4. **扩展阅读**：相关文档链接
5. **权威参考**：参考资料

### 4.3 版本信息

每个文档应包含版本信息：

```markdown
**版本信息**：
- **适用版本**：Redis 7.2+
- **文档基于版本**：Redis 7.2
- **最后更新**：2025-01
```

---

## 5. 提交规范

### 5.1 提交信息格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 5.2 提交类型

- `feat`：新功能
- `fix`：Bug修复
- `docs`：文档更新
- `style`：代码格式调整
- `refactor`：代码重构
- `test`：测试相关
- `chore`：构建过程或辅助工具变动

### 5.3 提交示例

```bash
# 新功能
git commit -m "feat(cache): 添加LRU缓存算法实现"

# Bug修复
git commit -m "fix(redis): 修复连接池泄漏问题"

# 文档更新
git commit -m "docs(readme): 更新项目说明文档"
```

---

## 6. 代码审查

### 6.1 审查流程

1. **提交PR**：创建Pull Request
2. **自动检查**：CI/CD自动检查
3. **人工审查**：维护者审查代码
4. **修改反馈**：根据反馈修改代码
5. **合并代码**：审查通过后合并

### 6.2 审查标准

- **代码质量**：代码符合规范
- **测试覆盖**：包含足够的测试
- **文档完整**：文档更新完整
- **性能考虑**：考虑性能影响

---

## 7. 行为准则

### 7.1 尊重他人

- 尊重所有贡献者
- 接受建设性批评
- 保持专业和礼貌

### 7.2 协作精神

- 积极回应反馈
- 及时更新PR
- 帮助其他贡献者

---

## 8. 联系方式

如有问题，请通过以下方式联系：

- **GitHub Issues**：提交Issue
- **GitHub Discussions**：参与讨论
- **邮件**：feedback@buffercache.org

---

**文档版本**：v1.0
**创建日期**：2025-01
**最后更新**：2025-01
**状态**：✅ 完成
