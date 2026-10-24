#!/usr/bin/env python3
"""多模态入库量计算器 — 各模态条目数、分块数、token 预算（对齐腾讯 ima 真实能力）

腾讯 ima 知识库能力边界（2026-09 核实）：
  - 直接支持入库：PDF / Word(.doc/.docx) / PPT(.ppt/.pptx) / Excel(.xls/.xlsx/.csv)
    / txt / Markdown / 图片(jpg/png，OCR 识别) / 音频(mp3/wav/m4a/aac，自动转写)
    / 网页 / 公众号 / 微信文件 / 笔记 / 腾讯文档 / Xmind
  - 视频(.mp4/.avi/.mov) 不支持直接上传！须预处理：
      ① 提取音轨 → 转音频文件（mp3/wav/m4a）入库（ima 自动 ASR 转写）
      ② 有价值画面 → 截图为图片（jpg/png）入库（ima OCR 识别）
      视频本身不进入知识库，入库量按"音轨 + 截图"两条派生路径估算
  - 护栏：单次批量 ≤50 文件；PDF 单文件 <100M；txt <200K；个人库默认 100G

闭式模型：
  文档：条目数 = 文件数；分块数 = 总页数 × 每页分块数
  图片：每图 1 条目（有文字走 OCR，纯图形走描述）
  音频：条目数 = 转写段落数（默认每段 60s）
  视频：不直接入库；派生两条路径——
        音轨路径：条目数 = 视频时长s / 60（按音频段落）
        截图路径：条目数 = 时长s × 截图fps（人工挑选关键帧截图后按图片入库）
        video_entries = audio_track_entries + screenshot_entries（并集去重上限取 max）
  token 预算 = Σ(各模态分块数 × 单块 token)
"""
import argparse, json, math, sys


def calc_doc_entries(file_count, pages_per_file, chunks_per_page):
    """文档条目数与分块数"""
    entries = max(0, file_count)
    chunks = max(0, file_count) * max(0, pages_per_file) * max(0.1, chunks_per_page)
    return entries, math.ceil(chunks)


def calc_audio_entries(duration_s, seg_seconds=60):
    """音频转写条目数（按段落切分）"""
    if duration_s <= 0:
        return 0
    return max(1, math.ceil(duration_s / seg_seconds))


def calc_video_entries(duration_s, fps, audio_track=True):
    """视频派生入库量（视频本身不支持直接入库，走音轨+截图两条派生路径）
    audio_track: 是否提取音轨转音频（ima 自动 ASR 转写）
    截图路径：时长s × 截图采样fps（人工挑选关键帧，存为图片走 OCR）
    """
    if duration_s <= 0:
        return 0, 0, 0
    # 路径①：提取音轨 → 按音频段落估算
    track_entries = calc_audio_entries(duration_s) if audio_track else 0
    # 路径②：关键帧截图 → 按图片条目估算
    screenshot_entries = int(max(0, duration_s) * max(0.0, fps))
    # 并集去重上限（同源内容不重复占条目，取较大路径作保守上限）
    total = max(track_entries, screenshot_entries)
    return track_entries, screenshot_entries, total


def estimate_tokens(chunks, chunk_tokens):
    return max(0, chunks) * max(0, chunk_tokens)


def main():
    p = argparse.ArgumentParser(description="多模态入库量计算（对齐腾讯 ima：视频走音轨+截图派生路径）")
    p.add_argument('--mode', choices=['by_modality', 'full'], default='full')
    p.add_argument('--docs', type=int, default=0, help='文档文件数（PDF/Word/PPT/Excel/MD/txt）')
    p.add_argument('--pages-per-file', type=int, default=10, help='平均页/文件')
    p.add_argument('--chunks-per-page', type=float, default=2, help='每页切块数')
    p.add_argument('--images', type=int, default=0, help='图片数（jpg/png，含 OCR 场景）')
    p.add_argument('--audio-seconds', type=float, default=0, help='音频总时长（秒），ima 自动 ASR 转写')
    p.add_argument('--video-seconds', type=float, default=0, help='视频总时长（秒）——不直接入库，走音轨+截图派生')
    p.add_argument('--fps', type=float, default=0.0, help='视频截图采样率（帧/秒，人工挑关键帧；0=不截图仅提音轨）')
    p.add_argument('--no-audio-track', action='store_true', help='视频不提取音轨（仅截图路径）')
    p.add_argument('--chunk-tokens', type=int, default=500, help='单块 token 预算')
    p.add_argument('--batch-files', type=int, default=0, help='本次批量导入文件数（ima 护栏：≤50/次）')
    args = p.parse_args()

    doc_entries, doc_chunks = calc_doc_entries(args.docs, args.pages_per_file, args.chunks_per_page)
    audio_entries = calc_audio_entries(args.audio_seconds)
    image_entries = max(0, args.images)
    v_track, v_shot, video_entries = calc_video_entries(args.video_seconds, args.fps, audio_track=not args.no_audio_track)

    total_entries = doc_entries + image_entries + audio_entries + video_entries
    total_chunks = doc_chunks + image_entries + audio_entries + video_entries
    total_tokens = estimate_tokens(total_chunks, args.chunk_tokens)

    result = {
        "by_modality": {
            "docs": {"entries": doc_entries, "chunks": doc_chunks},
            "images": {"entries": image_entries, "chunks": image_entries},
            "audio": {"entries": audio_entries},
            "video": {
                "note": "视频不支持直接入库，派生路径：音轨转音频 + 截图入图片",
                "audio_track_entries": v_track,
                "screenshot_entries": v_shot,
                "entries": video_entries,
            },
        },
        "total_entries": total_entries,
        "total_chunks": total_chunks,
        "total_tokens_budget": total_tokens,
        "chunk_tokens": args.chunk_tokens,
        "ima_guardrails": {
            "batch_limit_per_import": 50,
            "pdf_max_mb": 100,
            "txt_max_kb": 200,
            "personal_kb_default_gb": 100,
            "batch_ok": (args.batch_files <= 50) if args.batch_files else None,
        },
    }

    if args.mode == 'by_modality':
        print(json.dumps(result["by_modality"], ensure_ascii=False))
    else:
        print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
