#!/usr/bin/env python3
"""ima 采集源渠道计算器 — 八大渠道选型、≤50 分批、预转换、容量护栏
闭式模型：
  批次总数 = ⌈文件总数 / 单批上限(50)⌉
  预转换数 = 视频数(提音轨) + 超规格PDF数(拆) + 超大txt数(转格式)
  直接入库文件数 = 文档+图片+音频（ima 直接支持）
  容量占用 GB = (直接入库文件数 + 派生产物数) × 单文件均值MB / 1024
  与库容量(默认100G)对比 → capacity_ok
渠道白名单（ima 官方八大渠道）：
  local_file / local_folder / personal_kb / wechat_file / web_link / note / tencent_doc / voice_minutes
"""
import argparse, json, math, sys

CHANNELS = ["local_file", "local_folder", "personal_kb", "wechat_file",
            "web_link", "note", "tencent_doc", "voice_minutes"]
BATCH_LIMIT = 50          # 单次批量导入上限（ima 护栏）
PDF_MAX_MB = 100         # PDF 单文件上限
TXT_MAX_KB = 200         # txt 单文件上限
DEFAULT_KB_GB = 100      # 个人库默认容量


def is_known_channel(ch):
    return ch in CHANNELS


def batch_count(total_files, limit=BATCH_LIMIT):
    return max(1, math.ceil(max(0, total_files) / limit)) if total_files else 0


def pre_conversion_needed(videos, over_spec_pdfs, oversize_txts):
    """视频→音轨(1:1)；超规格PDF需拆分；超大txt需转格式。预转换件数 = 三者之和"""
    return max(0, videos) + max(0, over_spec_pdfs) + max(0, oversize_txts)


def direct_ingest_count(docs, images, audio_files):
    """ima 直接支持：文档/图片/音频"""
    return max(0, docs) + max(0, images) + max(0, audio_files)


def capacity_gb(total_items, avg_mb_per_item, kb_cap_gb=DEFAULT_KB_GB):
    usage = total_items * max(0.0, avg_mb_per_item) / 1024.0
    return {
        "usage_gb": round(usage, 2),
        "kb_cap_gb": kb_cap_gb,
        "capacity_ok": usage <= kb_cap_gb,
    }


def main():
    p = argparse.ArgumentParser(description="ima 采集源渠道计算（八大渠道白名单 + ≤50 分批 + 容量护栏）")
    p.add_argument('--mode', choices=['by_channel', 'full'], default='full')
    p.add_argument('--docs', type=int, default=0, help='文档文件数（PDF/Word/PPT/Excel/MD/txt）')
    p.add_argument('--images', type=int, default=0, help='图片文件数（jpg/png）')
    p.add_argument('--audio-files', type=int, default=0, help='音频文件数（mp3/wav/m4a/aac）')
    p.add_argument('--videos', type=int, default=0, help='视频文件数（须预转换提音轨，不直接入库）')
    p.add_argument('--over-spec-pdfs', type=int, default=0, help='超规格PDF数（>100M需拆分）')
    p.add_argument('--oversize-txts', type=int, default=0, help='超大txt数（>200K需转格式）')
    p.add_argument('--avg-mb', type=float, default=1.5, help='单文件均值MB（容量估算）')
    p.add_argument('--kb-cap-gb', type=float, default=DEFAULT_KB_GB, help='库容量GB（默认100）')
    p.add_argument('--channels', type=str, default='',
                   help='JSON 数组：本次使用的渠道白名单子集，如 ["local_file","wechat_file","web_link"]')
    args = p.parse_args()

    # 渠道白名单校验
    channels_used = []
    if args.channels:
        channels_used = json.loads(args.channels)
        unknown = [c for c in channels_used if not is_known_channel(c)]
        if unknown:
            print(json.dumps({"error": f"未知渠道 {unknown}，ima 官方仅支持 {CHANNELS}"}, ensure_ascii=False))
            sys.exit(1)

    pre_conv = pre_conversion_needed(args.videos, args.over_spec_pdfs, args.oversize_txts)
    direct = direct_ingest_count(args.docs, args.images, args.audio_files)
    # 入库批次按"直接入库文件 + 派生产物"计（预转换后的音轨/截图作为新文件入队）
    # 派生：视频提音轨≈视频数；此处保守把预转换件也计入待入队
    queue_items = direct + pre_conv
    batches = batch_count(queue_items)

    cap = capacity_gb(queue_items, args.avg_mb, args.kb_cap_gb)

    result = {
        "channels_whitelist": CHANNELS,
        "channels_used": channels_used if channels_used else "all",
        "pre_conversion_needed": pre_conv,
        "direct_ingest_files": direct,
        "total_queue_items": queue_items,
        "batch_limit_per_import": BATCH_LIMIT,
        "batch_count": batches,
        "capacity": cap,
        "guardrail_ok": cap["capacity_ok"],
    }

    if args.mode == 'by_channel':
        print(json.dumps({
            "channels_used": result["channels_used"],
            "pre_conversion_needed": pre_conv,
        }, ensure_ascii=False))
    else:
        print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
