"""core utilities —— 共享路径校验、配置、日志、审计与引导模块。"""

import io
import sys


def _ensure_utf8_stdio() -> None:
    """强制 stdout/stderr 使用 UTF-8。

    当输出被管道/重定向接管时，Python 会退回本地编码；在 POSIX/C locale 下
    该编码为 ASCII，任何中文字符都会触发 UnicodeEncodeError 并截断输出。
    以 UTF-8 重新打开标准流可避免此问题，保证文件名与正文完整。

    本函数幂等，且只改动 sys.stdout / sys.stderr，不影响用户终端与系统 locale。
    """
    for attr in ("stdout", "stderr"):
        stream = getattr(sys, attr)
        if stream is None:
            continue
        try:
            encoding = stream.encoding
        except AttributeError:
            encoding = None
        if encoding and encoding.lower() in ("utf-8", "utf_8", "cp65001"):
            continue
        # 以 UTF-8 重新打开底层文件描述符，保留行缓冲。
        try:
            fd = stream.fileno()
            if fd < 0:
                continue
        except (OSError, ValueError):
            continue
        try:
            # stdout/stderr 为只写：以二进制写模式打开该 fd，再以 UTF-8 文本写入器包装。
            new = io.TextIOWrapper(
                open(fd, "wb", closefd=False),
                encoding="utf-8",
                line_buffering=getattr(stream, "line_buffering", False),
                write_through=True,
            )
        except Exception:  # pragma: no cover
            continue
        setattr(sys, attr, new)


_ensure_utf8_stdio()
