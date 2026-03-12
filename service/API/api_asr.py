import asyncio
import base64
import hashlib
import hmac
import json
import time
import websockets
from urllib.parse import urlencode, urlparse, urlunparse
from fastapi import WebSocket, WebSocketDisconnect
import logging
import sys
import os
from dotenv import load_dotenv

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from service.utils.audio_processor import convert_webm_to_pcm

# 加载环境变量
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

logger = logging.getLogger(__name__)


class XfyunASRClient:
    """讯飞实时语音听写客户端"""

    def __init__(self, app_id: str, api_key: str, api_secret: str):
        self.app_id = app_id
        self.api_key = api_key
        self.api_secret = api_secret
        self.ws_url = "wss://iat-api.xfyun.cn/v2/iat"

    def generate_ws_auth_url(self) -> str:
        """生成 WebSocket 鉴权 URL"""
        u = urlparse(self.ws_url)
        host = u.hostname
        date = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())

        # 生成签名原文
        signature_origin = f"host: {host}\ndate: {date}\nGET {u.path} HTTP/1.1"

        # 使用 HMAC-SHA256 进行签名
        signature = hmac.new(
            self.api_secret.encode(),
            signature_origin.encode(),
            hashlib.sha256
        ).digest()
        signature_b64 = base64.b64encode(signature).decode()

        # 生成 Authorization 头
        authorization_origin = (
            f'api_key="{self.api_key}",algorithm="hmac-sha256",'
            f'headers="host date request-line",signature="{signature_b64}"'
        )
        authorization = base64.b64encode(authorization_origin.encode()).decode()

        # 构建查询参数
        query_params = {
            "host": host,
            "date": date,
            "authorization": authorization
        }

        # 构建完整 URL
        query_string = urlencode(query_params)
        full_url = urlunparse((
            u.scheme,
            u.netloc,
            u.path,
            u.params,
            query_string,
            u.fragment
        ))

        return full_url

    async def send_audio_frame(self, ws, status: int, audio_data: bytes = b""):
        """发送音频数据帧

        Args:
            ws: WebSocket连接
            status: 状态码 (0: 首帧, 1: 中间帧, 2: 结束帧)
            audio_data: 音频数据
        """
        frame = {
            "common": {"app_id": self.app_id},
            "business": {
                "language": "zh_cn",   # 中文
                "domain": "iat",       # 听写
                "accent": "mandarin",  # 普通话
                "dwa": "wpgs",         # 动态修正
            },
            "data": {
                "status": status,
                "format": "audio/L16;rate=16000",
                "encoding": "raw",
                "audio": base64.b64encode(audio_data).decode() if audio_data else ""
            }
        }

        await ws.send(json.dumps(frame))


async def process_audio_with_xfyun(
    audio_data: bytes,
    app_id: str,
    api_key: str,
    api_secret: str,
    result_callback=None
) -> str:
    """
    使用讯飞ASR处理音频数据

    Args:
        audio_data: PCM格式的音频数据
        app_id: 讯飞应用ID
        api_key: 讯飞API Key
        api_secret: 讯飞API Secret
        result_callback: 结果回调函数

    Returns:
        识别的文本
    """
    client = XfyunASRClient(app_id, api_key, api_secret)
    auth_url = client.generate_ws_auth_url()

    accumulated_result = ""
    last_output = ""

    async with websockets.connect(auth_url) as ws:
        # 发送首帧配置
        await client.send_audio_frame(ws, status=0)

        # 分块发送音频数据
        chunk_size = 1280
        total_sent = 0

        for i in range(0, len(audio_data), chunk_size):
            chunk = audio_data[i:i + chunk_size]
            await client.send_audio_frame(ws, status=1, audio_data=chunk)
            total_sent += len(chunk)
            await asyncio.sleep(0.04)

        logger.info(f"[讯飞ASR] 音频数据发送完成，共发送 {total_sent} 字节")

        # 发送结束帧
        await client.send_audio_frame(ws, status=2)

        # 接收识别结果
        while True:
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                response_data = json.loads(response)

                if response_data.get("code") == 0 and "data" in response_data:
                    if "result" in response_data["data"]:
                        # 提取识别文本
                        partial_text = ""
                        for ws_item in response_data["data"]["result"]["ws"]:
                            for cw in ws_item["cw"]:
                                partial_text += cw["w"]

                        if partial_text:
                            # 判断是否为最终结果
                            is_final = response_data["data"].get("status") == 2

                            if is_final:
                                # 最终结果，累积
                                accumulated_result += partial_text
                                current_result = accumulated_result
                            else:
                                # 中间结果
                                current_result = accumulated_result + partial_text

                            # 避免重复输出
                            if current_result != last_output:
                                logger.info(f"[讯飞ASR] 识别结果: {current_result}")
                                if result_callback:
                                    await result_callback(current_result)
                                last_output = current_result

                            # 如果收到结束标识，退出循环
                            if is_final:
                                break

            except asyncio.TimeoutError:
                # 超时，认为接收完成
                break
            except Exception as e:
                logger.error(f"[讯飞ASR] 接收数据错误: {e}")
                break

        logger.info(f"[讯飞ASR] 识别完成，最终结果: {accumulated_result}")
        return accumulated_result


# 讯飞配置 - 从环境变量读取
XFYUN_CONFIG = {
    "app_id": os.getenv("XFYUN_APP_ID"),
    "api_key": os.getenv("XFYUN_API_KEY"),
    "api_secret": os.getenv("XFYUN_API_SECRET")
}

# 验证配置
if not all([XFYUN_CONFIG["app_id"], XFYUN_CONFIG["api_key"], XFYUN_CONFIG["api_secret"]]):
    raise ValueError(
        "错误：未找到讯飞 ASR API 配置！\n"
        "请在 .env 文件中设置以下环境变量：\n"
        "  - XFYUN_APP_ID\n"
        "  - XFYUN_API_KEY\n"
        "  - XFYUN_API_SECRET\n"
        "获取地址：https://console.xfyun.cn/services/cbf"
    )


async def websocket_asr_endpoint(websocket: WebSocket):
    """
    WebSocket 语音转文字端点

    前端使用方法:
    1. 连接到 ws://host:port/audio/upload
    2. 发送二进制音频数据 (webm格式会自动转换为PCM)
    3. 接收识别结果
    """
    await websocket.accept()

    try:
        # 通知客户端准备就绪
        await websocket.send_json({
            "type": "ready",
            "message": "服务已就绪，请发送音频数据"
        })

        # 接收音频数据
        audio_data = await websocket.receive_bytes()
        logger.info(f"[ASR] 接收到音频数据，大小: {len(audio_data)} 字节")

        # 转换webm到PCM格式
        logger.info("[ASR] 正在转换音频格式 (webm -> PCM)...")
        pcm_data = await convert_webm_to_pcm(audio_data)

        if pcm_data is None:
            logger.error("[ASR] 音频格式转换失败")
            await websocket.send_json({
                "type": "error",
                "message": "音频格式转换失败，请确保已安装ffmpeg"
            })
            return

        logger.info(f"[ASR] 音频转换完成，PCM大小: {len(pcm_data)} 字节")

        async def send_result(text: str):
            """发送识别结果到前端"""
            await websocket.send_text(text)

        # 处理音频并获取识别结果
        result = await process_audio_with_xfyun(
            audio_data=pcm_data,
            app_id=XFYUN_CONFIG["app_id"],
            api_key=XFYUN_CONFIG["api_key"],
            api_secret=XFYUN_CONFIG["api_secret"],
            result_callback=send_result
        )

        # 发送结束信号
        await websocket.send_text("END")
        logger.info("[ASR] 处理完成")

    except WebSocketDisconnect:
        logger.info("[ASR] 客户端断开连接")
    except Exception as e:
        logger.error(f"[ASR] 处理错误: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"处理失败: {str(e)}"
            })
        except:
            pass
    finally:
        await websocket.close()
