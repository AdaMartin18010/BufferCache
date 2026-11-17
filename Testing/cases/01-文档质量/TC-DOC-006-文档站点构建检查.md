# TC-DOC-006 文档站点构建检查（mkdocs）

- **用例ID**：TC-DOC-006 | **优先级**：P2 | **自动化**：self_verify 已覆盖（`docs` 组，无 mkdocs 自动 SKIP）
- **目的**：验证 250+ 篇 docs/ 文档作为 MkDocs 站点可构建（--strict 模式），兑现文档自动化维护机制.md 的站点化设想
- **关联**：mkdocs.yml；[文档自动化维护机制](../../docs/00-项目总览/文档自动化维护机制.md)；requirements-dev.txt

## 步骤

```bash
pip install -r requirements-dev.txt     # 首次启用
python Testing/self_verify.py docs      # 含本检查项
# 或手工：mkdocs build --strict
```

## 预期结果

- 未装 mkdocs：SKIP（正常，不阻断）
- 已装：`mkdocs build` 成功（站点可构建为硬标准）；链接类 warning（GitHub 兼容锚点/跨目录仓库链接/archive 冻结文档）按**基线管理**——计数登记，突增即排查锚点漂移

## 基线与已知豁免（2026-11-17 首次构建测量）

| 类别 | 处置 |
| ---- | ---- |
| 文档目录自锚（GitHub slugify 兼容） | 基线豁免，计数监控 |
| 指向 docs/ 外仓库资产的链接（../AGENTS.md、../Testing/ 等） | 站点边界固有，基线豁免 |
| archive/ 冻结文档内链接 | 不参与站点构建（exclude），豁免 |
| 真实锚点漂移（标题改名后目录未同步） | **真缺陷**，必须修 |

## 失败纠正与修正指引

1. 构建失败：按报错文件修正（常见：YAML frontmatter 冲突、锚点重名、nav 引用缺失）。
2. --strict 下 warning 即失败：逐项修复（多为链接/锚点）。
3. 修正：新顶级文档应同步评估是否加入 mkdocs.yml nav（与 INDEX.md 导航义务并行）。
