# 讯飞文字转语音服务 (TTS)

基于讯飞开放平台 WebSocket API 的实时语音合成服务。

## 功能特性

- 🎤 **实时语音合成** - 支持流式音频返回
- 🗣️ **多种发音人** - 支持晓燕、晓峰、晓美、晓琪等多种发音人
- ⚙️ **参数可调** - 语速、音量、音高均可自定义
- 🎵 **多音频格式** - 支持 MP3、PCM、Speex 等格式
- 🔌 **WebSocket接口** - 实时双向通信，低延迟
- 🌐 **测试客户端** - 内置Web测试页面，方便调试

## 快速开始

### 1. 环境要求

- Python 3.8+
- 依赖库：`fastapi`, `websockets`, `uvicorn`

### 2. 安装依赖

```bash
pip install fastapi websockets uvicorn
```

### 3. 配置密钥

**⚠️ 安全提示**：在提交到Git仓库前，请将硬编码的密钥移到环境变量中！

编辑 `tts_service.py` 中的配置（第23-25行）：

```python
APP_ID = "你的讯飞AppID"
API_KEY = "你的讯飞API Key"
API_SECRET = "你的讯飞API Secret"
```

### 4. 启动服务

```bash
python tts_service.py
```

服务将在 `http://localhost:8003` 启动。

### 5. 测试服务

访问测试页面：`http://localhost:8003/client`

## API 接口说明

### WebSocket 端点

**端点**: `ws://localhost:8003/ws/tts`

#### 连接流程

1. 客户端连接 WebSocket
2. 服务返回 `{"type": "ready", ...}` 确认就绪
3. 客户端发送合成请求（JSON格式）
4. 服务返回音频数据（二进制）和状态消息（JSON）

#### 请求格式

```json
{
  "text": "要转换为语音的文本",
  "voice_name": "xiaoyan",    // 可选，发音人
  "speed": 50,                 // 可选，语速 0-100
  "volume": 50,                // 可选，音量 0-100
  "pitch": 50,                 // 可选，音高 0-100
  "audio_format": "lame"       // 可选，音频格式 lame/raw/speex
}
```

#### 响应格式

**状态消息（JSON）**：
```json
{
  "type": "ready|status|audio|complete|error",
  "message": "状态描述",
  "chunk_size": 1234,          // 仅 type=audio 时
  "total_size": 5678,          // 仅 type=complete 时
  "chunks": 3                  // 仅 type=complete 时
}
```

**音频数据（二进制）**：
- 当有音频数据时，直接发送二进制数据
- 音频格式取决于请求中的 `audio_format` 参数

### HTTP 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 服务信息 |
| `/health` | GET | 健康检查 |
| `/client` | GET | 测试客户端页面 |
| `/docs` | GET | API 文档 |

## 发音人列表

| voice_name | 名称 | 特点 |
|------------|------|------|
| xiaoyan | 晓燕 | 女声，情感柔和 |
| xiaofeng | 晓峰 | 男声，沉稳大气 |
| xiaomei | 晓美 | 女声，活泼开朗 |
| xiaoqi | 晓琪 | 女声，年轻活力 |

## 音频格式说明

| audio_format | 格式 | 说明 |
|--------------|------|------|
| lame | MP3 | 推荐，兼容性好 |
| raw | PCM | 未压缩，高质量 |
| speex | Speex | 压缩，低带宽 |

## 参数范围

| 参数 | 范围 | 默认值 | 说明 |
|------|------|--------|------|
| speed | 0-100 | 50 | 语速，值越大越快 |
| volume | 0-100 | 50 | 音量 |
| pitch | 0-100 | 50 | 音高 |

## 使用示例

### Python 客户端

```python
import asyncio
import websockets
import json

async def text_to_speech(text):
    uri = "ws://localhost:8003/ws/tts"

    async with websockets.connect(uri) as websocket:
        # 等待服务就绪
        ready = await websocket.recv()
        print(f"服务状态: {ready}")

        # 发送合成请求
        request = {
            "text": text,
            "voice_name": "xiaoyan",
            "speed": 50,
            "volume": 50,
            "pitch": 50,
            "audio_format": "lame"
        }
        await websocket.send(json.dumps(request))

        # 接收音频数据
        audio_data = b""
        while True:
            response = await websocket.recv()

            if isinstance(response, bytes):
                # 音频数据
                audio_data += response
            else:
                # 状态消息
                data = json.loads(response)
                print(f"状态: {data}")

                if data["type"] == "complete":
                    break
                elif data["type"] == "error":
                    raise Exception(data["message"])

        # 保存音频文件
        with open("output.mp3", "wb") as f:
            f.write(audio_data)

        print(f"音频已保存，大小: {len(audio_data)} 字节")

# 运行
asyncio.run(text_to_speech("你好，欢迎使用讯飞语音合成服务。"))
```

### JavaScript 客户端

```javascript
async function textToSpeech(text) {
  const ws = new WebSocket('ws://localhost:8003/ws/tts');
  const audioChunks = [];

  ws.onopen = () => {
    console.log('WebSocket连接成功');

    // 发送合成请求
    ws.send(JSON.stringify({
      text: text,
      voice_name: 'xiaoyan',
      speed: 50,
      volume: 50,
      pitch: 50,
      audio_format: 'lame'
    }));
  };

  ws.onmessage = async (event) => {
    if (typeof event.data === 'string') {
      // JSON状态消息
      const data = JSON.parse(event.data);
      console.log('状态:', data);

      if (data.type === 'complete') {
        console.log('合成完成');

        // 创建音频Blob并播放
        const audioBlob = new Blob(audioChunks, { type: 'audio/mpeg' });
        const audioUrl = URL.createObjectURL(audioBlob);
        const audio = new Audio(audioUrl);
        audio.play();

        ws.close();
      }
    } else {
      // 二进制音频数据
      audioChunks.push(event.data);
    }
  };

  ws.onerror = (error) => {
    console.error('WebSocket错误:', error);
  };
}

// 使用
textToSpeech('你好，欢迎使用讯飞语音合成服务。');
```

## 在项目中集成

### 前端集成（React/Next.js）

```typescript
// lib/env.ts
export const WS_TTS_URL = `ws://${API_HOST}:8003`;

// components/pre-diagnosis-page.tsx
const fetchTextToSpeech = async (text: string, messageId: string) => {
  const ws = new WebSocket(`${WS_TTS_URL}/ws/tts`);
  const audioChunks: Uint8Array[] = [];

  ws.onopen = () => {
    ws.send(JSON.stringify({
      text: text,
      voice_name: "xiaoyan",
      speed: 50,
      volume: 50,
      pitch: 50,
      audio_format: "lame"
    }));
  };

  ws.onmessage = async (event) => {
    if (event.data instanceof Blob) {
      const arrayBuffer = await event.data.arrayBuffer();
      audioChunks.push(new Uint8Array(arrayBuffer));
    } else {
      const data = JSON.parse(event.data);
      if (data.type === 'complete') {
        // 合成完成，创建音频URL
        const combinedBlob = new Blob(audioChunks, { type: 'audio/mpeg' });
        const audioUrl = URL.createObjectURL(combinedBlob);
        // 保存到消息中用于播放
        ws.close();
      }
    }
  };
};
```

## 故障排查

### 问题1：服务无法启动

**错误**: `Address already in use`

**解决**:
```bash
# 检查端口占用
lsof -i :8003  # Linux/Mac
netstat -ano | findstr :8003  # Windows

# 杀死占用进程
kill -9 <PID>
```

### 问题2：WebSocket连接失败

**可能原因**:
- 端口号错误
- 防火墙阻止
- 服务未启动

**解决**: 检查服务是否运行：`curl http://localhost:8003/health`

### 问题3：合成失败

**错误**: `讯飞服务错误: authentication failed`

**解决**: 检查密钥配置是否正确

**错误**: `错误：文本长度超过限制`

**解决**: 讯飞限制单次合成约2000汉字，请分批发送

### 问题4：音频无法播放

**可能原因**:
- 音频数据未完整接收
- 浏览器不支持该格式

**解决**: 使用 `lame` (MP3) 格式，兼容性最好

## 与ASR服务对比

| 对比项 | ASR | TTS |
|--------|-----|-----|
| 功能 | 语音转文字 | 文字转语音 |
| API端点 | `wss://iat-api.xfyun.cn/v2/iat` | `wss://tts-api.xfyun.cn/v2/tts` |
| 端口 | 8000 (通过后端) | 8003 (独立服务) |
| 发送数据 | 音频（PCM） | 文字（UTF-8） |
| 接收数据 | 文字识别结果 | 音频（MP3/PCM/Speex） |

## 许可证

本服务基于讯飞开放平台API，使用前请确保已获得相应授权。

## 获取密钥

访问 [讯飞开放平台](https://console.xfyun.cn/services/cbf) 申请：
1. 注册/登录账号
2. 创建应用
3. 开通语音合成服务
4. 获取 AppID、API Key、API Secret

## 相关文件

- `tts_service.py` - TTS服务主文件
- `service/API/api_asr.py` - ASR服务（语音转文字）
- `Frontend/app/components/pre-diagnosis-page.tsx` - 前端集成示例
- `Frontend/lib/env.ts` - 环境变量配置
