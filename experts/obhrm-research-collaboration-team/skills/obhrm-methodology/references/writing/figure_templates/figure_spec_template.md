# Figure Spec: [Figure Name]

<!-- This template captures everything needed to generate a non-data figure. -->
<!-- Fill it in by running /paper-writing figure spec mode, or manually. -->

## Identity

- **Figure ID:** fig:[short_id]
- **Paper section:** [e.g., §3 Design]
- **Placement:** [full-width (figure*) / single-column (figure)]
- **Archetype:** [architecture_overview | pipeline_flow | component_detail | concept_illustration | comparison_schematic | taxonomy | deployment_diagram]
- **Generation backend:** [ai_image]

## Purpose

- **Paper claim supported:** [the exact claim from project_context.md this figure serves]
- **What it shows:** [1-2 sentences — what should the reader understand after looking at this figure?]
- **Why this figure exists:** [what would be lost if it were removed?]
- **Role in narrative:** [motivation | design explanation | evidence summary | positioning]

## Content Specification

### Components

| Component | Label | Shape | Color | Description |
|-----------|-------|-------|-------|-------------|
| [name] | [display text] | [box / rounded / circle / diamond / cylinder / parallelogram] | [from palette] | [what it represents] |

### Connections

| From | To | Label | Style | Description |
|------|-----|-------|-------|-------------|
| [component] | [component] | [edge text or empty] | [arrow / dashed / bidirectional / none] | [what this connection represents] |

### Groupings

| Group | Contains | Label | Style |
|-------|----------|-------|-------|
| [name] | [comma-separated component list] | [display text, e.g., "Phase 1: Ingestion"] | [dashed border / shaded background] |

### Annotations

<!-- Callout boxes, dimension labels, example data snippets, or emphasis markers -->

- [annotation 1]
- [annotation 2]

## Layout

- **Flow direction:** [left-to-right / top-to-bottom / radial]
- **Hierarchy levels:** [how many vertical or horizontal tiers]
- **Symmetry constraints:** [any components that must be visually parallel, e.g., "encoder and decoder are symmetric"]
- **Size target:** [single-column (3.33in) / full-width (7.0in) — adjust per venue from venue_styles.md]

## Styling

- **Color mapping:** [which semantic category maps to which palette color]
- **Emphasis:** [which component is the paper's key contribution — should be visually prominent via color, border weight, or size]
- **Consistency notes:** [references to other figures in this paper whose style this must match]

## Generation

### For AI image backend

**Assembled prompt:**

<!-- 生成模式下由模型结合上方内容规格填充 -->
<!-- with the AI prompt styling block from venue_styles.md. -->
<!-- 也可将提示词直接粘贴到图像生成模型 -->

```
[Full generation prompt goes here]
```


## Caption

<!-- Interpretive, claim-first. States the takeaway, not just a description. -->
<!-- "NetBurst's three-stage pipeline transforms raw time series into event-centric -->
<!-- representations, enabling per-event feature extraction (§3.2) and embedding-based -->
<!-- similarity search (§3.3)." -->

**Draft caption:** [...]

## Status

- **Spec complete:** [yes / no]
- **Generated:** [yes / no — date if yes]
- **Critique passed:** [yes / no]
- **Iteration notes:** [what changed between versions]
