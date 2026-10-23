# LLM Wiki 宿主特例（llm-wiki-host）

> 适用成员：罗采（raw+sidecar）、苏航（交叉引用/实体页）、安档（log.md 只追加）
>
> **WorkBuddy 访问方式**：LLM Wiki 是本地文件夹，WorkBuddy 通过本地文件系统直接读写，**无需安装连接器**。用户只需提供 Wiki 根目录的本地路径。

## 1. 目录形态

```text
raw/        # 原始素材，只进不出
wiki/
  entities/ # 实体页：一份文件/一个对象一页
  concepts/ # 概念页：一个概念一页
  thinkings/ # 孵化区：未成熟内容（对应 idea/draft 池）
index.md    # 总索引
log.md      # 操作日志，只追加
```

## 2. raw + sidecar 入库模式

1. 原件复制进 `raw/`（文件名保留完整标识，禁止缩写）。
2. 同名 `.md` sidecar 记录元数据：标题、文号/标识、来源、日期、摘录、提炼去向回链。
3. 提炼产出实体页与概念页，正文结论必须可回溯 raw。
4. `raw/` 只进不出；不在 raw 写结论性分析；不编造来源。

## 3. 交叉引用与索引

- 实体页 ↔ 概念页互链；index.md 分类登记全部页面。
- 链接语法为 Markdown 相对链接（非 Obsidian `[[ ]]`）；link_integrity_scan.py 用 `--link-style markdown`。
- 新增页面同步登记 index.md 并追加 log.md。

## 4. 日志纪律

- `log.md` 只追加：create / update / move / delete（废除）各记原因与溯源。
- 废除优先「移入归档区或降级 thinkings」，硬删仅限用户显式确认；废除前排查互链引用方并清理。

## 5. 四池映射

| 四池 | LLM Wiki 落位 |
|---|---|
| idea / draft | wiki/thinkings/ |
| official | wiki/entities/ + wiki/concepts/（成熟后从 thinkings 迁移） |
| archive | 归档区（或页面打 archive 标记 + log 登记） |
