"""
音频处理工具模块
用于处理音频格式转换，特别是webm到PCM的转换
"""

import asyncio
import subprocess
import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def convert_webm_to_pcm(webm_data: bytes) -> Optional[bytes]:
    """
    将webm格式音频转换为PCM格式

    Args:
        webm_data: webm格式的音频数据

    Returns:
        PCM格式的音频数据，如果转换失败则返回None
    """
    try:
        # 使用 ffmpeg 将 webm 格式音频转换为 pcm 格式
        # -f s16le: 输出格式为PCM 16位小端
        # -ar 16000: 采样率16kHz
        # -ac 1: 单声道
        process = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-i", "pipe:0",  # 从stdin读取
            "-f", "s16le",   # PCM 16位小端
            "-ar", "16000",  # 采样率16kHz
            "-ac", "1",      # 单声道
            "-loglevel", "error",  # 只输出错误信息
            "pipe:1",        # 输出到stdout
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # 发送webm数据并获取PCM数据
        pcm_data, stderr = await process.communicate(input=webm_data)

        if process.returncode != 0:
            logger.error(f"[音频转换] ffmpeg转换失败: {stderr.decode()}")
            return None

        logger.info(f"[音频转换] 转换成功，输出大小: {len(pcm_data)} 字节")
        return pcm_data

    except FileNotFoundError:
        logger.error("[音频转换] 错误: 未找到ffmpeg，请确保已安装ffmpeg")
        return None
    except Exception as e:
        logger.error(f"[音频转换] 转换异常: {e}")
        return None


async def convert_any_audio_to_pcm(audio_data: bytes, input_format: str = "webm") -> Optional[bytes]:
    """
    将任意格式音频转换为PCM格式

    Args:
        audio_data: 输入音频数据
        input_format: 输入格式（webm, mp3, wav等）

    Returns:
        PCM格式的音频数据
    """
    return await convert_webm_to_pcm(audio_data)


def check_ffmpeg_installed() -> bool:
    """
    检查ffmpeg是否已安装

    Returns:
        True表示已安装，False表示未安装
    """
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
