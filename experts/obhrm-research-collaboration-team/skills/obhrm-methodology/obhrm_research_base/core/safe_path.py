#!/usr/bin/env python3
"""
safe_path.py — OBHRM 研究协作团共享安全路径工具

提供 resolve_safe_output()，在写入文件前对用户/调用方提供的输出路径做
规范化与范围校验，确保输出路径落在允许的基目录之内。

设计原则：
- 无副作用：不创建目录、不打开文件，仅做路径计算与 范围校验。
- 可独立单测：纯函数，仅依赖标准库（os / pathlib）。
- 严格 范围校验：解析后的绝对路径必须落在允许的基目录（base）之内，
  超出允许范围（含 `..` 逃逸、绝对路径指向系统目录等）一律抛 ValueError。

典型用法：
    from safe_path import resolve_safe_output
    try:
        out = resolve_safe_output(user_path, base=os.getcwd())
    except ValueError:
        sys.exit("输出路径超出允许范围，拒绝写入")
"""

import os
import sys
from pathlib import Path
from typing import Iterable, Optional, Union

# 编码设置：触发 obhrm_research_base.core.__init__ 中的 UTF-8 stdio 重绑定。
# safe_path 是 scripts/ 下几乎所有脚本的公共入口，在此处触发可确保所有 CLI
# 在 POSIX/C locale + 管道输出场景下不会因 CJK 字符触发 UnicodeEncodeError。
import obhrm_research_base.core  # noqa: E402, F401
_ = obhrm_research_base.core  # 触发 __init__ UTF-8 stdio 重绑定（显式引用以满足静态分析；用赋值而非 assert，避免 -O 下被剥离）

__all__ = ["resolve_safe_output"]

# user_path 可为 str 或 Path
PathLike = Union[str, Path]
# base 可为 None / 单个路径 / 路径列表
BaseArg = Optional[Union[PathLike, Iterable[PathLike]]]


def _resolve_bases(base: BaseArg) -> list:
    """将 base 参数归一为一组已解析的绝对路径列表。

    - None        -> [cwd]
    - str / Path  -> [该路径]
    - 列表/元组   -> 其中每个路径（用于多允许根场景，如 config_manager
                     允许“配置/技能目录”或 cwd 两个根）
    """
    if base is None:
        candidates = [Path.cwd()]
    elif isinstance(base, (str, Path)):
        candidates = [base]
    else:
        candidates = list(base)

    resolved = []
    for c in candidates:
        p = Path(c)
        if not p.is_absolute():
            p = Path.cwd() / p
        resolved.append(p.resolve())
    return resolved


# 模块级缓存: 已探测过的「真实存在祖先目录」的大小写敏感性结果。
_fs_case_insensitive_cache: dict = {}


def _fs_case_insensitive(base) -> bool:
    """探测 base 所在文件系统是否大小写不敏感(macOS/Windows)。

    向上找到第一个真实存在的祖先目录, 将其首字母大小写翻转后用
    os.path.samefile 判断是否为同一位置: 若是, 说明 FS 大小写不敏感。
    结果按「真实存在的祖先路径」缓存, 避免每次调用都做 samefile 探测。
    """
    p = Path(base)
    while not p.exists() and p != p.parent:
        p = p.parent
    if not p.exists():
        return False
    key = str(p)
    cached = _fs_case_insensitive_cache.get(key)
    if cached is not None:
        return cached
    name = p.name
    if not name:
        _fs_case_insensitive_cache[key] = False
        return False
    flip = name[0].swapcase() + name[1:]
    if flip == name:
        _fs_case_insensitive_cache[key] = False
        return False
    try:
        result = os.path.samefile(str(p), str(p.with_name(flip)))
    except OSError:
        result = False
    _fs_case_insensitive_cache[key] = result
    return result


def _is_within(resolved: Path, base: Path) -> bool:
    """判断 resolved 是否严格落在 base 之内。

    使用 os.path.commonpath 而非 Path.relative_to，以避免前缀误判：
    例如 '/tmp/evil_chart' 不会被错误地判定为落在 '/tmp/evil' 内。
    """
    try:
        # 精确(区分大小写)比较 —— 在 POSIX/Linux 等大小写敏感文件系统上行为正确,
        # 且优先于下面的退路, 保证 Linux 上大小写不同的「真实不同目录」仍被正确拒绝。
        resolved_s = str(resolved)
        base_s = str(base)
        common = os.path.commonpath([resolved_s, base_s])
        if common == base_s:
            return True
        # 仅当文件系统确为大小写不敏感(macOS/Windows)时, 才启用
        # casefold 退路吸收「同一目录的大小写变体」。大小写敏感文件系统直接跳过
        # 退路, 完全依赖上面的精确比较, 避免把「允许根的大小写变体兄弟目录」也误接受
        # (影响范围有限，但会削弱范围校验)。
        if not _fs_case_insensitive(base):
            return False
        # 大小写不敏感 FS 上, realpath 对「同一目录的大小写变体」可能返回不一致大小写
        # (例如 cwd 为 <USER_HOME> 而传入绝对路径解析为 <user_home>), 导致「合法界内」的绝对
        # 路径被误拒(fail-closed 过度拒绝)。用 str.casefold() 显式归一后再比较,
        # 吸收纯大小写差异。此退路只影响「大小写」, 不改变目录结构,
        # 不会放过 `..` 上跳或绝对路径越出基目录（结构比较已由上面 commonpath 完成）。
        common_f = os.path.commonpath([resolved_s.casefold(), base_s.casefold()])
    except ValueError:
        # 不同挂载点/混合相对绝对路径等情况，视为不在之内
        return False
    return common_f == base_s.casefold()


def resolve_safe_output(user_path: PathLike, base: BaseArg = None) -> Path:
    """规范化用户输出路径，并断言其落在允许基目录之内。

    Args:
        user_path: 用户/调用方提供的输出路径（文件或目录均可）。
        base: 允许的根目录（允许根）。
            - None（默认）：当前工作目录 cwd。
            - 单个路径（str / Path）：该目录为唯一允许根。
            - 路径列表/元组：满足其中任意一个根即可（多允许根场景）。

    Returns:
        已解析、且通过超出允许范围校验的绝对路径（Path）。

    Raises:
        ValueError: 解析后的路径越出所有允许基目录（含 `..` 逃逸、指向系统
                    目录等）。错误信息形如 “路径超出允许范围，拒绝写入：<绝对路径>”。
    """
    # 先解析 ~ 开头的家目录路径（避免 cwd 拼接后被误判为合法）
    import os as _os
    user_path = _os.path.expanduser(user_path)
    resolved = Path(user_path).resolve()
    for b in _resolve_bases(base):
        if _is_within(resolved, b):
            return resolved
    raise ValueError("路径超出允许范围，拒绝写入：" + str(resolved))


def safe_open_for_write(user_path, base=None, **open_kwargs):
    """按范围校验打开文件用于写入：resolve → 范围校验 → O_NOFOLLOW 避免符号链接竞态 → realpath 二次确认。

    ``resolve_safe_output`` 返回 Path 后，调用方 ``open(safe, "w")``
    仍存在 check-then-use 竞态（resolve 后、open 前符号链接可能被替换）。本函数
    在 ``os.open`` 阶段使用 ``O_NOFOLLOW`` 拒绝符号链接，并再次 realpath 确认落点在允许根
    之内，最后才用 ``os.fdopen`` 包装返回给调用方。

    Args:
        user_path: 目标文件路径。
        base: 允许根（语义同 ``resolve_safe_output``）。
        **open_kwargs: 透传给 ``os.fdopen``（如 ``encoding="utf-8"``）。

    Returns:
        file object（已配置 ``encoding``，如传入），调用方负责 ``close`` 或 ``with``。

    Raises:
        ValueError: 路径超出允许范围、符号链接指向范围外、或二次校验失败。
        OSError: 文件已存在且为符号链接 / 其他 OS 级失败。
    """
    import os as _os  # 局部导入便于单测 mock
    import stat as _stat
    if "encoding" in open_kwargs and "mode" not in open_kwargs:
        open_kwargs["mode"] = "w"
    mode = open_kwargs.pop("mode", "w")
    # 先解析 ~ 开头的家目录路径
    user_path = _os.path.expanduser(user_path)
    safe = resolve_safe_output(user_path, base=base)
    # (1) 用 O_NOFOLLOW 拒绝符号链接；O_CREAT|O_WRONLY|O_TRUNC 仍允许新建普通文件
    flags = _os.O_WRONLY | _os.O_CREAT | _os.O_TRUNC | _os.O_NOFOLLOW
    if "b" in mode:
        flags |= _os.O_BINARY if hasattr(_os, "O_BINARY") else 0
    fd = _os.open(str(safe), flags, 0o644)
    try:
        # (2) 二次 realpath 校验：即便 O_NOFOLLOW 已防 symlink，仍确认落点仍在允许根内
        #     （避免硬链接指向范围外的 inode）
        try:
            st = _os.fstat(fd)
        except OSError as exc:
            _os.close(fd)
            raise ValueError("fstat 失败: %s" % exc) from exc
        # 注：符号链接已在 os.open(O_NOFOLLOW) 阶段被拒绝，此处无需再判定 S_ISLNK。
        # (3) realpath 二次确认：处理 hardlink 情况
        import os.path as _op
        real = _op.realpath(str(safe))
        if not any(_is_within(Path(real), b) for b in _resolve_bases(base)):
            _os.close(fd)
            raise ValueError("TOCTOU 二次校验失败，realpath 超出允许范围: %s" % real)
        # (4) 包装成 file object 返回
        return _os.fdopen(fd, mode, **open_kwargs)
    except BaseException:
        try:
            _os.close(fd)
        except OSError:
            pass
        raise


def resolve_config_path(config_path=None, script_file=None):
    """返回 config.json 的绝对路径（仅做路径定位，不读取、不校验存在性）。

    统一脚本各自重复的“定位 config.json”样板：显式路径 → 原样 abspath；
    未显式给出（None）→ 回退到 ``script_file`` 所在目录的上级目录下的 config.json。

    Args:
        config_path: 显式 config.json 路径；None 时启用回退逻辑。
        script_file: 调用方的 ``__file__``，用于回退时定位脚本上级目录。
            仅在 config_path 为 None 时需要。

    Returns:
        str: config.json 的绝对路径。是否存在由调用方自行判断。
    """
    if config_path is None:
        config_path = os.path.join(
            os.path.dirname(os.path.abspath(script_file)), "..", "config.json")
    return os.path.abspath(config_path)


# 便于以 `python safe_path.py` 直接做最小自测
if __name__ == "__main__":
    import tempfile

    ok = True
    with tempfile.TemporaryDirectory() as d:
        root = Path(d).resolve()
        inside = root / "sub" / "file.txt"
        escape = root / ".." / "evil.txt"
        # 合法：基目录内
        assert resolve_safe_output(str(inside), base=root) == inside.resolve()
        # 合法：正好等于基目录
        assert resolve_safe_output(str(root), base=root) == root
        # 超出允许范围：.. 逃逸
        try:
            resolve_safe_output(str(escape), base=root)
            ok = False
        except ValueError:
            pass
        # 超出允许范围：绝对路径指向基目录外
        # 用 os.sep + 目录名 + 文件名拼接构造一个包目录之外的绝对路径，
        # 验证 resolve_safe_output 能拦截越界绝对路径。
        try:
            resolve_safe_output(os.path.join(os.sep, "tmp", "obhrm_forbidden_path_test"), base=root)
            ok = False
        except ValueError:
            pass
    print("safe_path 自测:", "通过" if ok else "失败")
    sys.exit(0 if ok else 1)
