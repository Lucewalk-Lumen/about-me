#!/usr/bin/env Rscript
# sna_r.R —— EndNote 共现网络的社会网络分析（R 增强后端）
#
# 设计原则（与 Python 主程序一致的契约）:
#   - igraph 为【必需】依赖（R + igraph 是计量分析的标准路径）。缺失时向
#     stderr 打印一条清晰的 G4 风格提示，并以非 0 退出码退出，**绝不**尝试自动安装。
#   - 所有"结果"以机器可读形式写入输出目录（CSV + JSON，UTF-8），
#     不依赖控制台美观输出，便于 Python 包装层解析。
#   - 任何非预期错误都打印到 stderr 并退出非 0。Python 端据此【直接失败】并给出
#     安装指引（缺 R 不再静默回退；仅当用户显式传 --allow-python-fallback 才降级）。
#
# 输入: 边表 CSV（列 from,to[,weight]），输出目录
# 用法: Rscript sna_r.R <edges.csv> <out_dir>
# 输出:
#   <out_dir>/sna_r_nodes.csv      node,degree,betweenness,closeness,eigen,community
#   <out_dir>/sna_r_summary.json   社群规模/模块度/密度/版本等

suppressPackageStartupMessages({
  # G4 门禁：缺失包则提示安装（不代装）
  ensure_pkg <- function(p) {
    if (!requireNamespace(p, quietly = TRUE)) {
      cat(paste0("G4: 未安装 R 包 ", p, "（R + ", p,
                 " 是标准路径的必需前置条件）。请先运行：\n",
                 "  Rscript -e 'install.packages(\"", p,
                 "\", lib=Sys.getenv(\"R_LIBS_USER\"), ",
                 "repos=\"https://mirrors.tuna.tsinghua.edu.cn/CRAN/\")'\n",
                 "  （装到用户库无需管理员权限；Rscript 不在 PATH 时用完整路径）"),
          file = stderr())
      cat("\n", file = stderr())
      quit(status = 2)
    }
    library(p, character.only = TRUE)
  }
  ensure_pkg("igraph")
})

run <- function() {
  args <- commandArgs(trailingOnly = TRUE)
  if (length(args) < 2) {
    cat("用法: Rscript sna_r.R <edges.csv> <out_dir>\n", file = stderr())
    quit(status = 1)
  }
  edges_path <- args[1]
  out_dir    <- args[2]

  if (!file.exists(edges_path)) {
    cat(paste0("G3: 边表文件不存在: ", edges_path, "\n"), file = stderr())
    quit(status = 1)
  }

  # 边表由 sna_r.py 以 UTF-8（无 BOM）写出，节点名含中文。
  # Windows 中文区域设置下，read.csv() 会在连接层按 GBK 推断编码，
  # 对无 BOM 的 UTF-8 报 "invalid input found on input connection"。
  # 解法：以二进制连接读入原始字节 → 显式按 UTF-8 解码 → 再交给 read.csv 解析文本。
  # 该方式不依赖区域设置，已在中文 Windows 上实测通过。
  dat <- local({
    con <- file(edges_path, open = "rb")
    on.exit(close(con), add = TRUE)
    raw <- readBin(con, what = "raw", n = file.size(edges_path))
    txt <- rawToChar(raw)
    Encoding(txt) <- "UTF-8"
    # 去掉可能存在的 UTF-8 BOM（会污染首列名）
    if (startsWith(txt, "\ufeff")) txt <- substring(txt, 2)
    txt <- gsub("\r\n", "\n", txt, fixed = TRUE)
    utils::read.csv(text = txt, stringsAsFactors = FALSE, check.names = FALSE)
  })
  req <- c("from", "to")
  miss <- setdiff(req, names(dat))
  if (length(miss) > 0) {
    cat(paste0("G3: 边表缺少必需列: ", paste(miss, collapse = ", "), "\n"),
        file = stderr())
    quit(status = 1)
  }

  # ── 空边表守卫 ────────────────────────────────────────────
  # 注意：实测发现，当网络被 --min-edge 过滤后可能一条边都不剩
  # （小库常见：各主题内关键词共现不足）。此时 graph_from_data_frame
  # 造出 0 节点图，后续 modularity/edge_density 全部返回 NaN，
  # eigen_centrality 还会刷一串 "no non-missing arguments to max" 警告。
  # 结果是 Python 端拿到 n_nodes=0 却仍报 backend="R" 成功 ——
  # 用户以为拿到了交叉验证结果，实际什么也没有。
  # 故此处显式判空并以**内部信号 3** 退出；sna_r.py 收到后拒接 n_nodes=0 的结果，
  # 按环境不满足硬失败（exit 8）——不再自动回退（除非显式 --allow-python-fallback）。
  if (nrow(dat) == 0) {
    cat("G5: 边表为空（0 条边），无法做社会网络分析。\n", file = stderr())
    cat(paste0("     提示: 共现网络需先跑 build_network.py；若已跑过，",
               "请降低 --min-edge 或 --node-df。\n"), file = stderr())
    quit(status = 3)
  }

  # 关键词共现网络本质是无向的（(a,b) 与 (b,a) 等价，边表每对只出现一次，
  # 无任何方向语义）。构建为无向图才能得到有意义的中心性 / 社群结构：
  # 有向图下 eigen_centrality 因图不强连通会退化为常数（全部相等 -> 归一化为 0）。
  use_weight <- "weight" %in% names(dat)
  if (use_weight) {
    g <- graph_from_data_frame(dat[, c("from", "to", "weight")], directed = FALSE)
  } else {
    g <- graph_from_data_frame(dat[, c("from", "to")], directed = FALSE)
  }

  # ── 中心性 ──────────────────────────────────────────────
  deg <- degree(g, mode = "all")
  bet <- betweenness(g, directed = is_directed(g), normalized = FALSE)
  clo <- closeness(g, mode = "all", normalized = TRUE)
  # v1.0.0：不连通图下 closeness 的 normalized 形式会对孤立/跨分量节点
  # 返回 NaN/NA；betweenness 在极稀疏分量里也可能出 NA。统一把 NA/NaN/Inf
  # 置 0 —— 否则写出 CSV 出现空字段，Python 端 float("") 直接崩
  # （实测 6,344 篇库：'punishment' 节点 closeness 写出空 → float(None)）。
  bet[!is.finite(bet)] <- 0
  clo[!is.finite(clo)] <- 0

  # [!]  igraph 2.1.1 起 eigen_centrality(scale=) 已废弃，恒按 scale=TRUE 处理。
  #    版本比较**必须用 package_info / 版本对象比较**：
  #    as.numeric(packageVersion("igraph")) 会抛
  #    "'list' object cannot be coerced to type 'double'"（packageVersion
  #    返回的是 package_version 类列表），被 tryCatch 吞掉后恒为 0，
  #    导致永远走旧版分支、每次都刷 deprecation 警告。
  #    另注意：只取 major（2）也不对 —— 2 >= 2.1 为 FALSE。
  need_scale_arg <- tryCatch({
    packageVersion("igraph") < "2.1"
  }, error = function(e) {
    cat(paste0("[warn] 无法判定 igraph 版本（", conditionMessage(e),
               "），按新版处理不传 scale。\n"), file = stderr())
    FALSE
  })
  eig_raw <- tryCatch(
    if (need_scale_arg) {
      eigen_centrality(g, directed = is_directed(g), scale = TRUE)
    } else {
      eigen_centrality(g, directed = is_directed(g))
    },
    error = function(e) {
      cat(paste0("[warn] eigen_centrality 失败（可能图不连通），回退为 0: ",
                 conditionMessage(e), "\n"), file = stderr())
      NULL
    }
  )
  if (is.null(eig_raw)) {
    eig <- rep(0, vcount(g))
  } else {
    eig <- as.numeric(eig_raw$vector)
    # 归一化到 0–1，便于与 Python 侧度数对比（特征向量本身可含负值）
    # 守卫：全常数向量时 max-min=0，直接归一化会产生 NaN/Inf
    rng <- max(eig) - min(eig)
    if (is.finite(rng) && rng > 0) {
      eig <- (eig - min(eig)) / rng
    } else {
      eig <- rep(0, vcount(g))
    }
  }

  # ── 社群检测（walktrap 为主；louvain 若存在则一并比较）────────
  comm <- cluster_walktrap(g)
  walk_mod <- modularity(comm)

  lou_mod <- NA_real_
  if (exists("cluster_louvain")) {
    comm_lou <- tryCatch(cluster_louvain(g), error = function(e) NULL)
    if (!is.null(comm_lou)) lou_mod <- modularity(comm_lou)
  }

  mem <- as.numeric(membership(comm))
  names(mem) <- V(g)$name

  # 社群规模（按 size 降序）
  comm_sizes <- sort(table(mem), decreasing = TRUE)
  communities <- lapply(seq_along(comm_sizes), function(i) {
    list(id = as.integer(names(comm_sizes)[i]),
         size = as.integer(comm_sizes[i]))
  })

  # ── 节点级结果 CSV ──────────────────────────────────────
  nodes_df <- data.frame(
    node          = V(g)$name,
    degree        = as.numeric(deg),
    betweenness   = round(as.numeric(bet), 6),
    closeness     = round(as.numeric(clo), 6),
    eigen         = round(as.numeric(eig), 6),
    community     = as.integer(mem),
    stringsAsFactors = FALSE
  )
  # v1.0.0：拼接 CSV 前把任何残留的 NA/NaN 数值列置 0，
  # 保证每行恒为 6 列（paste0(NA) 会产出 "NA"，下游按空解析）。
  for (col in c("degree", "betweenness", "closeness", "eigen", "community")) {
    v <- nodes_df[[col]]
    v[!is.finite(v)] <- 0
    nodes_df[[col]] <- v
  }

  if (!dir.exists(out_dir)) dir.create(out_dir, recursive = TRUE)
  # R 的 write.csv 会把非 ASCII 字符转义成 <U+XXXX> 形式（实测中文关键词
  # 全部变成 "<U+5458><U+5DE5>"，报告里彻底乱码），且给连接传 fileEncoding
  # 不生效（该参数仅对 path 形式有效）。故显式做一次编码转换：
  # 先按 UTF-8 写出（禁止转义），再统一补 BOM 供下游 Python 识别。
  nodes_out <- file.path(out_dir, "sna_r_nodes.csv")
  con <- file(nodes_out, open = "wb")
  writeLines(
    enc2utf8(c(
      paste0('"node","degree","betweenness","closeness","eigen","community"'),
      vapply(seq_len(nrow(nodes_df)), function(i) {
        paste0('"', gsub('"', '""', nodes_df$node[i], fixed = TRUE), '",',
               nodes_df$degree[i], ',', nodes_df$betweenness[i], ',',
               nodes_df$closeness[i], ',', nodes_df$eigen[i], ',',
               nodes_df$community[i])
      }, character(1))
    )),
    con = con, useBytes = TRUE
  )
  close(con)  # 必须先关闭连接 flush 到磁盘，否则下方 readBin 回读到空文件（1.0.1 修：nodes.csv 仅剩 BOM）
  # 前置 UTF-8 BOM（R 无法直接写 BOM，手工拼字节）
  bom <- as.raw(c(0xEF, 0xBB, 0xBF))
  body <- readBin(nodes_out, what = "raw", n = file.size(nodes_out))
  unlink(nodes_out)
  con2 <- file(nodes_out, open = "wb")
  writeBin(c(bom, body), con2)
  close(con2)

  # ── 汇总 JSON（手写，避免依赖 jsonlite）──────────────────
  # 版本信息
  r_ver <- paste(R.version$major, R.version$minor, sep = ".")
  ig_ver <- as.character(packageVersion("igraph"))

  # communities 序列化为 "{\"id\":k,\"size\":s},..." 形式
  comm_str <- paste(
    vapply(communities, function(c) {
      paste0("{\"id\":", c$id, ",\"size\":", c$size, "}")
    }, character(1)),
    collapse = ","
  )

  summary_txt <- paste0(
    "{\n",
    "  \"n_nodes\": ", vcount(g), ",\n",
    "  \"n_edges\": ", ecount(g), ",\n",
    "  \"directed\": ", tolower(as.character(is_directed(g))), ",\n",
    "  \"weighted\": ", tolower(as.character(use_weight)), ",\n",
    "  \"modularity\": ", round(walk_mod, 6), ",\n",
    "  \"louvain_modularity\": ",
        if (is.na(lou_mod)) "null" else round(lou_mod, 6), ",\n",
    "  \"density\": ", round(edge_density(g), 6), ",\n",
    "  \"n_communities\": ", length(communities), ",\n",
    "  \"communities\": [", comm_str, "],\n",
    "  \"r_version\": \"", r_ver, "\",\n",
    "  \"igraph_version\": \"", ig_ver, "\"\n",
    "}"
  )
  writeLines(summary_txt, file.path(out_dir, "sna_r_summary.json"),
             useBytes = TRUE)

  cat("OK\n", file = stderr())
  quit(status = 0)
}

# 顶层容错：任何未捕获错误都打印到 stderr 并退出非 0（Python 端据此降级）
res <- tryCatch(run(), error = function(e) {
  cat(paste0("[error] sna_r.R 运行失败: ", conditionMessage(e), "\n"),
      file = stderr())
  quit(status = 1)
})
