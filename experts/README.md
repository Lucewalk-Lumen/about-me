# experts/ 专家包迁入规则

1. 每个包一个目录,目录名 = `plugin.json` 的 `name`(kebab-case);
2. 迁入前必须通过预检(见 `docs/PRECHECK.md`):无本机绝对路径、无未授权第三方素材、发布残留已清理;
3. 保持 `.codebuddy-plugin/` 目录结构不变;
4. 包内自带 README / LICENSE / CHANGELOG 的,保留原文件。
