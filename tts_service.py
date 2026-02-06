#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
讯飞文字转语音服务 (TTS)
基于 WebSocket 实现实时语音合成
ASR服务的相反功能：ASR是语音→文字，TTS是文字→语音
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
import websockets
import base64
import hashlib
import hmac
import time
import json
import asyncio
from urllib.parse import urlparse, urlunparse, urlencode
from typing import Optional

# ==================== 配置区域 ====================
# 请替换为您在讯飞开放平台申请的真实密钥
APP_ID = "81e6886d"
API_KEY = "786aff06a2faf15ce5120c9b59546e40"
API_SECRET = "ODc2OGVjMDQzYWU2YTE4NjVmZmEwYmVl"

# 讯飞 TTS 服务地址
XF_TTS_URL = "wss://tts-api.xfyun.cn/v2/tts"
# ===================================================

app = FastAPI(title="讯飞文字转语音服务", description="TTS - Text To Speech")


def generate_ws_auth_url(api_url: str) -> str:
    """
    生成 WebSocket 鉴权 URL
    参考讯飞开放平台鉴权算法
    """
    u = urlparse(api_url)
    host = u.hostname
    date = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())

    # 生成签名原文
    signature_origin = f"host: {host}\ndate: {date}\nGET {u.path} HTTP/1.1"

    # 使用 HMAC-SHA256 进行签名
    signature = hmac.new(
        API_SECRET.encode(),
        signature_origin.encode(),
        hashlib.sha256
    ).digest()
    signature_b64 = base64.b64encode(signature).decode()

    # 生成 Authorization 头
    authorization_origin = (
        f'api_key="{API_KEY}",algorithm="hmac-sha256",'
        f'headers="host date request-line",signature="{signature_b64}"'
    )
    authorization = base64.b64encode(authorization_origin.encode()).decode()

    # 构建查询参数
    query_params = {
        "host": host,
        "date": date,
        "authorization": authorization
    }

    # 构建完整 URL - 使用 urlencode 进行正确的 URL 编码
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


@app.get("/")
def home():
    """服务首页"""
    return {
        "service": "讯飞文字转语音服务 (TTS)",
        "version": "1.0.0",
        "websocket_endpoint": "ws://localhost:8003/ws/tts",
        "description": "实时语音合成，支持多种发音人和音频格式",
        "supported_features": {
            "voices": ["xiaoyan", "xiaofeng", "xiaomei", "xiaoqi"],
            "audio_formats": ["mp3", "pcm", "speex"],
            "sample_rates": [8000, 16000]
        },
        "endpoints": {
            "websocket": "/ws/tts - WebSocket语音合成接口",
            "test_client": "/client - 测试客户端页面",
            "docs": "/docs - API文档"
        }
    }


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return JSONResponse({
        "status": "healthy",
        "service": "tts_service",
        "timestamp": time.time(),
        "app_id": APP_ID
    })


@app.websocket("/ws/tts")
async def websocket_tts(websocket: WebSocket):
    """
    WebSocket 文字转语音端点

    使用方法:
    1. 连接到 ws://localhost:8003/ws/tts
    2. 发送JSON格式的文本配置
    3. 接收二进制音频数据
    4. 自动完成语音合成

    消息格式:
    - 发送: JSON格式
      {
        "text": "要转换为语音的文本",
        "voice_name": "xiaoyan",     // 可选，发音人
        "speed": 50,                  // 可选，语速0-100
        "volume": 50,                 // 可选，音量0-100
        "pitch": 50,                  // 可选，音高0-100
        "audio_format": "lame"        // 可选，音频格式
      }
    - 接收: 二进制音频数据 或 JSON状态消息
      {
        "type": "ready|audio|complete|error",
        "message": "状态消息",
        "audio_size": 音频大小
      }
    """
    await websocket.accept()

    try:
        # 通知客户端准备就绪
        await websocket.send_json({
            "type": "ready",
            "message": "服务已就绪，请发送要合成的文本",
            "supported_voices": ["xiaoyan", "xiaofeng", "xiaomei", "xiaoqi"],
            "audio_formats": ["lame(mp3)", "raw(pcm)", "speex"]
        })

        # 接收客户端配置
        client_data = await websocket.receive_json()

        # 提取参数
        text = client_data.get("text", "")
        voice_name = client_data.get("voice_name", "xiaoyan")
        speed = client_data.get("speed", 50)
        volume = client_data.get("volume", 50)
        pitch = client_data.get("pitch", 50)
        audio_format = client_data.get("audio_format", "lame")

        # 参数验证
        if not text or not text.strip():
            await websocket.send_json({
                "type": "error",
                "message": "错误：文本不能为空"
            })
            return

        # 文本长度限制检查
        if len(text.encode('utf-8')) > 8000:
            await websocket.send_json({
                "type": "error",
                "message": "错误：文本长度超过限制（最多约2000汉字）"
            })
            return

        await websocket.send_json({
            "type": "status",
            "message": f"开始合成语音，文本长度: {len(text)} 字符"
        })

        # 生成鉴权 URL 并连接讯飞服务
        auth_url = generate_ws_auth_url(XF_TTS_URL)

        async with websockets.connect(auth_url) as xf_ws:
            # 构建请求帧
            request_frame = {
                "common": {"app_id": APP_ID},
                "business": {
                    "vcn": voice_name,      # 发音人
                    "speed": speed,         # 语速
                    "volume": volume,       # 音量
                    "pitch": pitch,         # 音高
                    "bgs": 0,              # 无背景音
                    "tte": "UTF8"          # 文本编码格式
                },
                "data": {
                    "status": 2,  # 一次性发送所有数据
                    "text": base64.b64encode(text.encode('utf-8')).decode()
                }
            }

            # 根据音频格式设置参数
            if audio_format == "lame":
                request_frame["business"]["aue"] = "lame"
                request_frame["business"]["sfl"] = 1  # mp3需要开启流式返回
            elif audio_format == "raw":
                request_frame["business"]["aue"] = "raw"
            elif audio_format == "speex":
                request_frame["business"]["aue"] = "speex"

            # 设置采样率
            request_frame["business"]["auf"] = "audio/L16;rate=16000"

            # 发送请求到讯飞
            await xf_ws.send(json.dumps(request_frame))

            await websocket.send_json({
                "type": "status",
                "message": "已连接讯飞语音服务，开始接收音频数据"
            })

            # 接收音频数据
            total_audio_size = 0
            audio_chunks = []

            while True:
                try:
                    # 接收讯飞响应
                    xf_response = await asyncio.wait_for(xf_ws.recv(), timeout=10.0)
                    response_data = json.loads(xf_response)

                    # 检查返回码
                    if response_data.get("code") != 0:
                        error_msg = response_data.get("message", "Unknown error")
                        await websocket.send_json({
                            "type": "error",
                            "message": f"讯飞服务错误: {error_msg}"
                        })
                        return

                    # 获取音频数据
                    data = response_data.get("data", {})
                    if data and "audio" in data:
                        # 解码base64音频数据
                        audio_base64 = data["audio"]
                        audio_bytes = base64.b64decode(audio_base64)
                        audio_chunks.append(audio_bytes)
                        total_audio_size += len(audio_bytes)

                        # 发送音频数据给客户端
                        await websocket.send_bytes(audio_bytes)

                        await websocket.send_json({
                            "type": "audio",
                            "message": "收到音频数据块",
                            "chunk_size": len(audio_bytes),
                            "total_size": total_audio_size
                        })

                    # 检查是否结束
                    if data and data.get("status") == 2:
                        await websocket.send_json({
                            "type": "complete",
                            "message": "语音合成完成",
                            "audio_size": total_audio_size,
                            "chunks": len(audio_chunks)
                        })
                        break

                except asyncio.TimeoutError:
                    await websocket.send_json({
                        "type": "error",
                        "message": "接收音频数据超时"
                    })
                    break

    except WebSocketDisconnect:
        print("✓ 客户端正常断开连接")
    except Exception as e:
        # 尝试向客户端发送错误信息
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"错误: {str(e)}"
            })
        except:
            pass
        print(f"✗ TTS错误: {e}")


@app.get("/client")
async def test_client():
    """
    提供一个简单的 HTML 测试客户端
    访问 http://localhost:8003/client 使用
    """
    html_content = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>文字转语音测试客户端</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 20px;
            }
            .container {
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                padding: 40px;
                max-width: 700px;
                width: 100%;
            }
            h1 {
                color: #333;
                margin-bottom: 10px;
                font-size: 28px;
            }
            .subtitle {
                color: #666;
                margin-bottom: 30px;
                font-size: 14px;
            }
            .status {
                padding: 15px;
                border-radius: 10px;
                margin-bottom: 20px;
                font-size: 14px;
            }
            .status.connected {
                background: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }
            .status.disconnected {
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }
            .status.pending {
                background: #fff3cd;
                color: #856404;
                border: 1px solid #ffeeba;
            }
            .input-group {
                margin-bottom: 20px;
            }
            label {
                display: block;
                margin-bottom: 8px;
                color: #333;
                font-weight: 600;
                font-size: 14px;
            }
            textarea, input, select {
                width: 100%;
                padding: 12px;
                border: 2px solid #e9ecef;
                border-radius: 10px;
                font-size: 14px;
                transition: border-color 0.3s;
            }
            textarea:focus, input:focus, select:focus {
                outline: none;
                border-color: #667eea;
            }
            textarea {
                min-height: 100px;
                resize: vertical;
            }
            .slider-group {
                display: flex;
                align-items: center;
                gap: 15px;
            }
            .slider-group input[type="range"] {
                flex: 1;
            }
            .slider-value {
                min-width: 40px;
                text-align: center;
                font-weight: 600;
                color: #667eea;
            }
            .controls {
                display: flex;
                gap: 15px;
                margin-top: 20px;
            }
            button {
                flex: 1;
                padding: 15px 30px;
                font-size: 16px;
                border: none;
                border-radius: 10px;
                cursor: pointer;
                transition: all 0.3s;
                font-weight: 600;
            }
            .btn-convert {
                background: #667eea;
                color: white;
            }
            .btn-convert:hover:not(:disabled) {
                background: #5568d3;
                transform: translateY(-2px);
            }
            .btn-play {
                background: #28a745;
                color: white;
            }
            .btn-play:hover:not(:disabled) {
                background: #218838;
                transform: translateY(-2px);
            }
            button:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }
            .audio-player {
                margin-top: 20px;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 10px;
                display: none;
            }
            .audio-player.show {
                display: block;
            }
            audio {
                width: 100%;
            }
            .info {
                margin-top: 15px;
                padding: 15px;
                background: #e7f3ff;
                border-radius: 10px;
                font-size: 14px;
                color: #333;
            }
            .log {
                margin-top: 20px;
                padding: 15px;
                background: #f8f9fa;
                border-radius: 10px;
                font-size: 12px;
                color: #666;
                max-height: 150px;
                overflow-y: auto;
            }
            .log-entry {
                margin: 5px 0;
                padding: 5px;
                border-radius: 5px;
            }
            .log-entry.info {
                background: #e7f3ff;
            }
            .log-entry.success {
                background: #d4edda;
            }
            .log-entry.error {
                background: #f8d7da;
                color: #721c24;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔊 文字转语音</h1>
            <p class="subtitle">基于讯飞开放平台的实时语音合成</p>

            <div id="status" class="status pending">
                状态: 等待连接...
            </div>

            <div class="input-group">
                <label>输入文本</label>
                <textarea id="textInput" placeholder="请输入要转换为语音的文本...">你好，欢迎使用讯飞语音合成服务。这是一个测试。</textarea>
            </div>

            <div class="input-group">
                <label>发音人</label>
                <select id="voiceSelect">
                    <option value="xiaoyan">晓燕（女声，情感柔和）</option>
                    <option value="xiaofeng">晓峰（男声，沉稳大气）</option>
                    <option value="xiaomei">晓美（女声，活泼开朗）</option>
                    <option value="xiaoqi">晓琪（女声，年轻活力）</option>
                </select>
            </div>

            <div class="input-group">
                <label>语速</label>
                <div class="slider-group">
                    <input type="range" id="speedRange" min="0" max="100" value="50">
                    <span class="slider-value" id="speedValue">50</span>
                </div>
            </div>

            <div class="input-group">
                <label>音量</label>
                <div class="slider-group">
                    <input type="range" id="volumeRange" min="0" max="100" value="50">
                    <span class="slider-value" id="volumeValue">50</span>
                </div>
            </div>

            <div class="input-group">
                <label>音高</label>
                <div class="slider-group">
                    <input type="range" id="pitchRange" min="0" max="100" value="50">
                    <span class="slider-value" id="pitchValue">50</span>
                </div>
            </div>

            <div class="input-group">
                <label>音频格式</label>
                <select id="formatSelect">
                    <option value="lame">MP3（推荐，兼容性好）</option>
                    <option value="raw">PCM（未压缩）</option>
                    <option value="speex">Speex（压缩）</option>
                </select>
            </div>

            <div class="controls">
                <button id="btnConvert" class="btn-convert" onclick="convertToSpeech()">
                    🔊 转换为语音
                </button>
                <button id="btnPlay" class="btn-play" onclick="playAudio()" disabled>
                    ▶️ 播放音频
                </button>
            </div>

            <div id="audioPlayer" class="audio-player">
                <audio id="audioElement" controls></audio>
                <div class="info" id="audioInfo"></div>
            </div>

            <div id="log" class="log">
                <div class="log-entry info">日志输出区域</div>
            </div>
        </div>

        <script>
            let ws = null;
            let audioBlob = null;
            let audioUrl = null;

            // 滑块值更新
            document.getElementById('speedRange').addEventListener('input', function() {
                document.getElementById('speedValue').textContent = this.value;
            });
            document.getElementById('volumeRange').addEventListener('input', function() {
                document.getElementById('volumeValue').textContent = this.value;
            });
            document.getElementById('pitchRange').addEventListener('input', function() {
                document.getElementById('pitchValue').textContent = this.value;
            });

            function log(message, type = 'info') {
                const logDiv = document.getElementById('log');
                const time = new Date().toLocaleTimeString();
                const entry = document.createElement('div');
                entry.className = `log-entry ${type}`;
                entry.textContent = `[${time}] ${message}`;
                logDiv.insertBefore(entry, logDiv.firstChild);
            }

            function updateStatus(text, status) {
                const statusDiv = document.getElementById('status');
                statusDiv.textContent = `状态: ${text}`;
                statusDiv.className = `status ${status}`;
            }

            async function convertToSpeech() {
                const text = document.getElementById('textInput').value.trim();

                if (!text) {
                    log('请输入要转换的文本', 'error');
                    return;
                }

                if (text.length > 2000) {
                    log('文本长度超过限制（最多2000字）', 'error');
                    return;
                }

                const voiceName = document.getElementById('voiceSelect').value;
                const speed = parseInt(document.getElementById('speedRange').value);
                const volume = parseInt(document.getElementById('volumeRange').value);
                const pitch = parseInt(document.getElementById('pitchRange').value);
                const audioFormat = document.getElementById('formatSelect').value;

                log('开始连接语音合成服务...', 'info');
                updateStatus('正在连接...', 'pending');

                // 禁用按钮
                document.getElementById('btnConvert').disabled = true;
                document.getElementById('btnPlay').disabled = true;

                try {
                    // 连接 WebSocket
                    ws = new WebSocket('ws://' + window.location.host + '/ws/tts');

                    ws.onopen = () => {
                        log('WebSocket连接成功', 'success');
                        updateStatus('正在合成...', 'connected');

                        // 发送合成请求
                        ws.send(JSON.stringify({
                            text: text,
                            voice_name: voiceName,
                            speed: speed,
                            volume: volume,
                            pitch: pitch,
                            audio_format: audioFormat
                        }));
                    };

                    ws.onmessage = async (event) => {
                        if (typeof event.data === 'string') {
                            // JSON消息
                            const data = JSON.parse(event.data);

                            if (data.type === 'ready') {
                                log('服务准备就绪', 'success');
                            } else if (data.type === 'status') {
                                log(data.message, 'info');
                            } else if (data.type === 'audio') {
                                log(`收到音频数据: ${data.chunk_size} 字节`, 'info');
                            } else if (data.type === 'complete') {
                                log(`合成完成，总大小: ${data.audio_size} 字节`, 'success');
                                updateStatus('合成完成', 'connected');
                                document.getElementById('btnPlay').disabled = false;
                            } else if (data.type === 'error') {
                                log(`错误: ${data.message}`, 'error');
                                updateStatus('错误', 'disconnected');
                                document.getElementById('btnConvert').disabled = false;
                            }
                        } else {
                            // 二进制音频数据
                            if (!audioBlob) {
                                audioBlob = new Blob([event.data], { type: 'audio/mpeg' });
                            } else {
                                audioBlob = new Blob([audioBlob, event.data], { type: 'audio/mpeg' });
                            }
                        }
                    };

                    ws.onerror = (error) => {
                        log('WebSocket错误', 'error');
                        updateStatus('连接错误', 'disconnected');
                        document.getElementById('btnConvert').disabled = false;
                    };

                    ws.onclose = () => {
                        log('WebSocket连接已关闭', 'info');
                        document.getElementById('btnConvert').disabled = false;
                    };

                } catch (error) {
                    log(`转换失败: ${error.message}`, 'error');
                    updateStatus('转换失败', 'disconnected');
                    document.getElementById('btnConvert').disabled = false;
                }
            }

            function playAudio() {
                if (!audioBlob) {
                    log('没有可播放的音频', 'error');
                    return;
                }

                // 创建音频URL
                if (audioUrl) {
                    URL.revokeObjectURL(audioUrl);
                }
                audioUrl = URL.createObjectURL(audioBlob);

                // 设置音频源并播放
                const audioElement = document.getElementById('audioElement');
                audioElement.src = audioUrl;

                // 显示信息
                const format = document.getElementById('formatSelect').value;
                document.getElementById('audioInfo').textContent =
                    `音频格式: ${format.toUpperCase()}, 大小: ${audioBlob.size} 字节`;
                document.getElementById('audioPlayer').classList.add('show');

                log('开始播放音频', 'success');
                audioElement.play();
            }

            // 页面加载完成
            window.onload = () => {
                log('页面加载完成', 'success');
                log('输入文本后点击"转换为语音"按钮', 'info');
            };

            // 页面关闭时清理
            window.onbeforeunload = () => {
                if (ws) {
                    ws.close();
                }
                if (audioUrl) {
                    URL.revokeObjectURL(audioUrl);
                }
            };
        </script>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)


if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("🚀 讯飞文字转语音服务 (TTS)")
    print("=" * 60)
    print(f"📌 服务地址: http://localhost:8003")
    print(f"📚 API文档: http://localhost:8003/docs")
    print(f"🖥️  测试客户端: http://localhost:8003/client")
    print("=" * 60)
    print("🔌 WebSocket 端点:")
    print(f"   ws://localhost:8003/ws/tts")
    print("=" * 60)
    print("🎯 支持的功能:")
    print("   - 多种发音人（晓燕、晓峰等）")
    print("   - 可调节语速、音量、音高")
    print("   - 多种音频格式（MP3、PCM、Speex）")
    print("   - 实时流式音频返回")
    print("=" * 60)
    print("💡 使用提示:")
    print("   1. 访问 /client 页面进行测试")
    print("   2. 输入要转换的文本")
    print("   3. 选择发音人和参数")
    print("   4. 点击'转换为语音'按钮")
    print("   5. 等待合成完成后点击'播放音频'")
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8003)
