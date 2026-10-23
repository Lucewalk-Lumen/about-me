# 交付指南：从 MD 到多格式


## 交付等级说明（D1 / D2）

| 等级 | 名称 | 条件 | 说明 |
|------|------|------|------|
| **D1** | 完整 HTML 交付 | 无需 Node 环境 | 以 `assets/report-template.html` 为模板（占位符替换式），内联 `assets/style.css` 与 `assets/mermaid.min.js`，产出**单文件自包含 HTML** |
| **D2** | Markdown 终稿交付 | 通用（无 HTML 渲染需求时） | 直接交付 Markdown 终稿。**禁止以 D2 对外声明「已完成 HTML 交付」**；须在文件头标注「Markdown 终稿，非 HTML 交付」 |

> **[注意] 禁止 D2 冒充 D1**：本指南明确禁止将未经模板化渲染的裸 Markdown，或仍引用外部文件 / 远程脚本的 HTML，对外声明为已交付的完整 HTML 终稿。

---

## 步骤摘要

### D1 路径（单文件自包含 HTML）

1. 以**本书根**维护终稿 Markdown（及 `.fbs/` 元数据）。
2. 以 `assets/report-template.html` 为模板，逐一替换其中的占位符（如 `{{COURSE_TOPIC}}`、`{{HERO_PILLS_HTML}}`、`{{FRAMEWORK_TREE_HTML}}` 等）；文本型占位符须先做 HTML 转义（`html.escape`）。
3. **内联** `assets/style.css` 与 `assets/mermaid.min.js`，产出**单文件 HTML**——不得保留任何外部文件引用或远程脚本引用，确保离线双击即可打开。
4. 交付前自检：双击打开样式与交互完整；确认页面不发起任何对外网络请求。
5. PDF / DOCX：如需额外格式，走宿主提供的 `pdf` / `docx` 插件交付链。

### D2 路径（Markdown 终稿）

1. 维护并交付 Markdown 终稿，**不得**对外声明为 HTML 交付。
2. 若需 HTML 呈现，按上文 **D1 路径**生成单文件 HTML 后再交付。
