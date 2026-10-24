# 编辑运行时契约（editor-runtime）

> **浏览器内编辑运行时**作为 make 线生成物与 edit 线注入的**统一底座**。
> 目标：让任意 deck 在浏览器内即可增删改、重排、保存、导出，无需回到生成器。
> 由 `build_deck.py`（生成时内嵌）与 `edit_deck.py`（注入已有 HTML）共用同一份 `RUNTIME_BLOCK`。

## 一、DOM 契约（必须遵循）

```
<section class="slide" id="slide-N" data-idx="N">     ← 每页一个，id 稳定
  <div class="obj" data-slide-object data-oid="oK" style="left/top/width">  ← 可移动内容单元
      ... 可编辑文本（带 data-edit）/ 图片 / 视频 ...
  </div>
</section>
```

- **每页**：`<section class="slide">` 具稳定 `id`（如 `slide-0`）；切页用 `.active` 类，**禁** `display:none`（用 `visibility`+`opacity`）。
- **可移动内容**：置于 `<div class="obj" data-slide-object data-oid="...">`，绝对定位（left/top/width）。`data-oid` 为对象唯一标识，编辑/撤销依赖它。
- **静态装饰**（背景、固定导航、页码）：置于 `.obj` 之外，不参与对象选择/拖拽。
- **可编辑文本**：`data-edit` 标记，`contentEditable` 由编辑模式统一开关。

## 二、浏览器内能力清单

| 能力 | 操作 | 说明 |
|------|------|------|
| 进入/退出编辑 | `E` / `Esc`；HUD「编辑」按钮 | 切换 `contentEditable` 与选择态 |
| 对象选择 | 单击 `.obj` | 加 `.sel` 描边并附 4 角 `.rz` 缩放柄 |
| 多选 | `Ctrl/Cmd/Shift+单击` | 累加选择，可批量移动 |
| 移动 | 拖拽对象体 | 实时改 left/top（按舞台缩放比换算） |
| 缩放 | 拖拽四角 `.rz` | 改 width/height，对顶角固定 |
| 删除 | `Delete`/`Backspace` | 移除选中对象，记入撤销栈 |
| 增元素 | HUD「+文字 / +图片 / +视频」 | 新建带 `data-oid` 的 `.obj`，默认置中 |
| Pages 侧栏 | `P` 或「Pages」按钮 | 缩略图列表（0.135 缩放克隆） |
| 重排 | 侧栏缩略图拖拽 | `reorderPage(from,to)` 重排 DOM 顺序 |
| 复制页 | 侧栏「复制」 | `copyPage(i)` 克隆插入下一页 |
| 删页 | 侧栏「删」 | `delPage(i)`，保留至少一页 |
| +New 页 | HUD / `newPage()` | 插入空白内容页 |
| 撤销/重做 | `Ctrl+Z` / `Ctrl+Y` | 快照栈（上限 60），覆盖移动/缩放/增删/重排 |
| 本地保存 | `Ctrl+S` | 写入 `localStorage`（key=`ppt-maker-draft::<title>`）+ Toast 提示 |
| 导出干净 HTML | HUD「导出干净」 | 剥离 `[data-edit]`/`contentEditable`/`.rz`/HUD/rail；`<img>` 远程图转 data URL；仅保留 NAV_JS 演示脚本，输出单文件 |
| 激光笔 | `L` 或「激光」按钮 | 跟随指针的红点光晕，演示用 |
| 全屏 | `F` 或「全屏」按钮 | `requestFullscreen` |

## 三、键位总表

```
E 编辑开/关    Esc 退出编辑    P Pages 侧栏    L 激光    F 全屏
S 演讲者模式   T 循环切换主题（13 套）
Ctrl+S 保存    Ctrl+Z 撤销     Ctrl+Y 重做     Delete 删除选中
←/→/Space 翻页 Home/End 首末页
```

> S / T 由 NAV 运行时提供（不属编辑运行时，但全产物可用）；`?preview=N` / `?presenter=1` 模式下编辑运行时不初始化（`__QS_EDIT` 守卫）。

## 四、与 build_deck 的关系

- **make 线**：`build_deck.py` 在生成阶段即把 `RUNTIME_BLOCK`（CSS+NAV+EDITOR+HUD）内嵌进单 HTML——生成的 deck 默认可编辑（场景 A）。
- **edit 线**：`edit_deck.py` 读取任意已有 HTML（含本技能 deck、含 `<section class="slide">` 的文稿、或普通 HTML 会被包成单页），执行 `ensure_stage → backfill_slides_and_objects → inject_runtime`，把同一份运行时**注入**，使其变为可编辑（场景 B/C）。
- **转换重编辑**：`extract_pptx.py` / `extract_pdf.py` 抽出 `deck-spec.json`，再经 `build_deck.py` 生成可编辑 HTML（场景 C）。

## 五、实现注意

- 运行时纯原生 JS，零依赖；`RUNTIME_BLOCK` 在 `build_deck.py` 中定义为唯一事实源，`edit_deck.py` 经 `import` 复用，避免双份漂移。
- 缩放/移动按 `stage.getBoundingClientRect().width/1920` 换算，确保缩放态下坐标系一致。
- 导出干净 HTML 对远程 `<img>` 用 `fetch→blob→dataURL` 内联（异步），离线也能自包含。
- 历史快照为 `stage.innerHTML` 字符串，`undo/redo` 直接回灌并 `refresh()` 重建选择态——简单稳健，适合中等规模 deck。
