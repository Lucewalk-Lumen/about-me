# 半自动化 CLI 调用示例

```bash
SKILL=skills/course-builder

# Step 1 · 输入闸门：验证 + 模式 / 深度判定
python3 $SKILL/scripts/validate_input.py \
    --input input.json --out build_plan.json --pretty

# Step 2-3 · LLM 按 build_plan 的 next_step_for_llm 产出 framework_tree（单顶层 dict）
#         → 写入 tree.json + (可选) questions.json

# Step 4 · 装配：自动算 tree_stats / provenance_summary / warnings，校验 100/5 上限
python3 $SKILL/scripts/assemble_result.py \
    --input input.json --tree tree.json --questions questions.json \
    --out result.json --pretty

# Step 7 · Provenance 审计（topic_only → skipped；material_first/hybrid → ngram 匹配）
python3 $SKILL/scripts/verify_provenance.py \
    --result result.json [--material textbook.md notes.md] \
    --out provenance-audit.json --pretty

# Step 8 · 4 格式渲染（banner 自动驱动）
python3 $SKILL/scripts/render_outputs.py result.json
#  → framework.md / framework.mindmap.html / framework.mermaid.md / framework.opml
```

**端到端 dogfood 参考**：`demos/knowledge-framework-builder/result-fixtures/topic-only-cet/`

所有 5 脚本退出码语义化（`0=ok / 1=参数错 / 2=约束违反或非法输入`），便于 CI 集成。
