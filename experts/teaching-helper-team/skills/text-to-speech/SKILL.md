---
name: text-to-speech
description: "免费语音合成：微软 Edge TTS（40+ 语言 300+ 声音），支持 rate/pitch/volume 精细控制，输出 MP3+SRT 字幕。零成本做课程/汇报/答辩音频。"
version: 1.1.1
---

# Edge TTS 免费语音合成
> **归属**：领域技能层——语音合成专家（text-to-speech）


> 微软 Edge 在线 TTS 的 Python 库/CLI，免费开源（MIT 许可），是教学帮帮团的**语音合成工具**。零成本生成课程讲解、汇报旁白、答辩演练音频。

## 安装

本团 Python 依赖统一装进 **WorkBuddy 托管 venv**（`~/.workbuddy/binaries/python/envs/teaching-helper-team/`，由 `setup` 首次会话自动安装），**通常无需手动 pip 安装**。调用 CLI 时请用 venv 解释器（其 bin 目录未必在系统 PATH 中）：

```bash
# venv 解释器路径随平台而异：macOS/Linux 为 <venv>/bin/python，Windows 为 <venv>\Scripts\python.exe。
# 确切路径已由 setup 写入 ~/.workbuddy/teaching-helper-team/setup-status.json 的 venv_python 字段。
VENV_PY="$HOME/.workbuddy/binaries/python/envs/teaching-helper-team/bin/python"   # Windows 请改为 .../Scripts/python.exe
"$VENV_PY" -m edge_tts --help
```

如需手动安装（脱离 setup 场景）：
```bash
pip install edge-tts          # Python 库（Python ≥3.7）
pipx install edge-tts         # 仅用 CLI 时（pipx 会把命令放入 PATH）
# 镜像（如网络受限可换为内部或地区镜像，但请遵守所在组织/机构的使用规范）
pip install edge-tts -i https://pypi.org/simple
```

> **PATH 说明**：若裸 `edge-tts` 提示 not found，是 venv/脚本 bin 目录未在 PATH —— 改用 `<venv>/bin/python -m edge_tts`（模块方式，跨平台一致）即可，无需重装。

**禁止** pip 安装非官方 ffmpeg 包（投毒风险）；单段合成优先 `--write-media` 规避 ffmpeg 依赖。

## 基本用法

```bash
# 文本转 MP3 + SRT 字幕（以 venv 模块方式调用，跨平台一致；VENV_PY 见上节）
"$VENV_PY" -m edge_tts \
  --text "你好，欢迎来到教学帮帮团" --voice zh-CN-XiaoxiaoNeural \
  --write-media output.mp3 --write-subtitles output.srt

# 列出全部音色
"$VENV_PY" -m edge_tts --list-voices
```

## 参数控制

- `--voice <name>`：音色（如 zh-CN-XiaoxiaoNeural 中文女声 / zh-CN-YunxiNeural 男声 / en-US-AriaNeural 英语）
- `--rate=-15%`：语速（-50% ~ +100%，教学场景可放缓）
- `--volume=+20%`：音量
- `--pitch=+10Hz`：音高（负值用 `--pitch=-50Hz` 写法）

## Python API

```python
import asyncio
from edge_tts import Communicate

async def tts():
    communicate = Communicate(
        text="这是教学演示音频",
        voice="zh-CN-XiaoxiaoNeural",
        rate="+0%",
    )
    await communicate.save("output.mp3")

asyncio.run(tts())
```

## 输出规范

- 音频产物写入数据总线 `data/pipeline/outgoing/`（MP3 + SRT），命名 `{task_id}_tts.{format}`
- 长文本按约 200 字/块分块合成后合并
- 需联网；仅白名单官方端点（speech.platform.bing.com 等）；不缓存音频到凭证域
- 合成留痕：voice/rate/pitch/volume/chunk_count 记录到 t_audio_job
