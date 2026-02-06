# 讯飞语音识别服务 (ASR)

基于讯飞开放平台 WebSocket API 的实时语音转文字服务。

## 功能特性

- 🎤 **实时语音识别** - 支持流式识别结果返回
- 🗣️ **中文听写** - 支持普通话识别
- 🔄 **动态修正** - 使用 wpgs 算法实现中间结果修正
- ⚡ **低延迟** - WebSocket 实时双向通信
- 🔌 **简单接口** - WebSocket 端点，易于集成
- 🎵 **多格式支持** - 自动转换 webm 到 PCM 格式

## 快速开始

### 1. 环境要求

- Python 3.8+
- 依赖库：`fastapi`, `websockets`, `uvicorn`
- 系统工具：`ffmpeg`（用于音频格式转换）

### 2. 安装依赖

```bash
pip install fastapi websockets uvicorn
```

### 3. 安装 ffmpeg

**Ubuntu/Debian**:
```bash
sudo apt-get install ffmpeg
```

**macOS**:
```bash
brew install ffmpeg
```

**Windows**:
下载并安装：https://ffmpeg.org/download.html

### 4. 配置密钥

编辑 `service/API/api_asr.py` 中的配置（第198-202行）：

```python
XFYUN_CONFIG = {
    "app_id": "你的讯飞AppID",
    "api_key": "你的讯飞API Key",
    "api_secret": "你的讯飞API Secret"
}
```

### 5. 启动后端服务

```bash
cd /home/hcc/project/xxl/MedSynthAI
python service/api_server.py
```

服务将在 `http://localhost:8000` 启动。

## API 接口说明

### WebSocket 端点

**端点**: `ws://localhost:8000/audio/upload`

#### 连接流程

1. 客户端连接 WebSocket
2. 服务返回 `{"type": "ready", ...}` 确认就绪
3. 客户端发送音频数据（二进制 webm 格式）
4. 服务自动转换为 PCM 格式
5. 调用讯飞 API 进行识别
6. 实时返回识别文字
7. 识别完成发送 `END` 标记

#### 请求格式

- **数据类型**: 二进制音频数据
- **音频格式**: webm（自动转换为 PCM）
- **采样率**: 16kHz
- **编码**: 16bit, 单声道

#### 响应格式

**控制消息（JSON）**：
```json
{
  "type": "ready",
  "message": "服务已就绪，请发送音频数据"
}
```

**识别文字（纯文本）**：
```
你好
```

**结束标记**：
```
END
```

### 与后端API的集成

ASR 服务通过 `service/api_server.py` 的 WebSocket 路由注册：

```python
@app.websocket("/audio/upload")
async def websocket_asr_handler(websocket: WebSocket):
    await websocket_asr_endpoint(websocket)
```

## 技术细节

### 音频处理流程

```
前端录音 (webm)
    ↓
WebSocket 发送
    ↓
后端接收
    ↓
ffmpeg 转换 (webm → PCM)
    ↓
讯飞 API 识别
    ↓
返回识别文字
```

### 讯飞 API 参数

| 参数 | 值 | 说明 |
|------|-----|------|
| language | zh_cn | 中文 |
| domain | iat | 听写 |
| accent | mandarin | 普通话 |
| dwa | wpgs | 动态修正 |
| format | audio/L16;rate=16000 | PCM 格式 |
| encoding | raw | 原始编码 |

## 使用示例

### Python 客户端

```python
import asyncio
import websockets

async def speech_to_text(audio_file_path):
    uri = "ws://localhost:8000/audio/upload"

    async with websockets.connect(uri) as websocket:
        # 等待服务就绪
        ready = await websocket.recv()
        print(f"服务状态: {ready}")

        # 读取音频文件
        with open(audio_file_path, "rb") as f:
            audio_data = f.read()

        # 发送音频数据
        await websocket.send(audio_data)
        print("音频已发送")

        # 接收识别结果
        result = ""
        while True:
            response = await websocket.recv()

            if response == "END":
                print("识别完成")
                break

            result = response
            print(f"识别结果: {result}")

        return result

# 运行
asyncio.run(speech_to_text("test_audio.webm"))
```

### JavaScript 客户端（浏览器录音）

```javascript
let mediaRecorder;
let audioChunks = [];

// 开始录音
async function startRecording() {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });

  mediaRecorder.ondataavailable = (e) => {
    audioChunks.push(e.data);
  };

  mediaRecorder.onstop = async () => {
    const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
    const arrayBuffer = await audioBlob.arrayBuffer();

    // 连接 WebSocket
    const ws = new WebSocket('ws://localhost:8000/audio/upload');

    ws.onopen = () => {
      console.log('WebSocket 连接成功');
      // 发送音频数据
      ws.send(arrayBuffer);
    };

    ws.onmessage = (event) => {
      const result = event.data;

      if (result === 'END') {
        console.log('识别完成');
        ws.close();
        return;
      }

      // 跳过 JSON 控制消息
      if (result.startsWith('{')) {
        return;
      }

      // 显示识别文字
      console.log('识别结果:', result);
      document.getElementById('input').value = result;
    };

    ws.onerror = (error) => {
      console.error('WebSocket 错误:', error);
    };
  };

  mediaRecorder.start();
}

// 停止录音
function stopRecording() {
  mediaRecorder.stop();
}
```

### React/Next.js 集成示例

```typescript
const [isRecording, setIsRecording] = useState(false);
const [input, setInput] = useState("");

const toggleRecording = async () => {
  if (isRecording) {
    mediaRecorder?.stop();
    setIsRecording(false);
    return;
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const audioChunks: Blob[] = [];

    const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });

    recorder.ondataavailable = (e) => {
      audioChunks.push(e.data);
    };

    recorder.onstop = async () => {
      const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
      const ws = new WebSocket(`ws://localhost:8000/audio/upload`);

      ws.onopen = async () => {
        const arrayBuffer = await audioBlob.arrayBuffer();
        ws.send(arrayBuffer);
      };

      let longestText = "";

      ws.onmessage = (event) => {
        const result = event.data;

        if (result === "END") {
          ws.close();
          stream.getTracks().forEach(track => track.stop());
          return;
        }

        // 跳过 JSON 消息
        if (result.startsWith("{") || result.includes("type")) {
          return;
        }

        // 保留最长的结果（讯飞返回累积结果）
        if (result.length > longestText.length) {
          longestText = result;
          setInput(longestText);
        }
      };

      ws.onerror = () => {
        ws.close();
      };
    };

    recorder.start();
    setMediaRecorder(recorder);
    setIsRecording(true);
  } catch (err) {
    console.error("录音失败:", err);
  }
};
```

## 音频格式转换

### 为什么需要转换？

- **浏览器录音格式**: webm（Opus 编码）
- **讯飞 API 要求**: PCM（未压缩）
- **转换工具**: ffmpeg

### audio_processor.py

```python
async def convert_webm_to_pcm(webm_data: bytes) -> Optional[bytes]:
    """
    将 webm 格式音频转换为 PCM 格式

    Args:
        webm_data: webm 格式的音频数据

    Returns:
        PCM 格式的音频数据，失败返回 None
    """
    # 使用 ffmpeg 进行转换
    # ...
```

## 故障排查

### 问题1：音频格式转换失败

**错误**: `音频格式转换失败，请确保已安装ffmpeg`

**解决**:
```bash
# 检查 ffmpeg 是否安装
ffmpeg -version

# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg
```

### 问题2：WebSocket 连接失败

**可能原因**:
- 后端服务未启动
- 端口号错误
- 防火墙阻止

**解决**:
```bash
# 检查服务是否运行
curl http://localhost:8000/

# 检查端口
netstat -tlnp | grep 8000
```

### 问题3：识别结果为空

**可能原因**:
- 音频数据未正确发送
- 音频质量太差
- 讯飞 API 密钥错误

**解决**: 检查浏览器控制台和后端日志

### 问题4：麦克风权限被拒绝

**错误**: `Permission denied`

**解决**:
- 确保网站使用 HTTPS 或 localhost
- 在浏览器设置中允许麦克风权限
- 检查系统隐私设置

## 已知限制

| 限制 | 说明 |
|------|------|
| 录音时长 | 单次最长 60 秒（讯飞 API 限制）|
| 音频格式 | 仅支持 webm 转 PCM |
| 语言 | 仅支持中文普通话 |
| 采样率 | 固定 16kHz |

## 依赖项

### Python 依赖

```
fastapi>=0.68.0
websockets>=10.0
uvicorn>=0.15.0
python-multipart>=0.0.5
```

### 系统依赖

```
ffmpeg 4.0+
```

## 与 TTS 服务对比

| 对比项 | ASR | TTS |
|--------|-----|-----|
| 功能 | 语音转文字 | 文字转语音 |
| API端点 | `wss://iat-api.xfyun.cn/v2/iat` | `wss://tts-api.xfyun.cn/v2/tts` |
| 本地端口 | 8000 (通过后端) | 8003 (独立服务) |
| 发送数据 | 音频（webm→PCM） | 文字（UTF-8） |
| 接收数据 | 文字识别结果 | 音频（MP3/PCM/Speex）|
| 文件位置 | `service/API/api_asr.py` | `tts_service.py` |

## 项目集成

### 前端集成要点

1. **引入环境变量**（`Frontend/lib/env.ts`）:
```typescript
export const WS_BASE_URL = `ws://${API_HOST}:${API_PORT}`;
```

2. **添加录音按钮**（`pre-diagnosis-page.tsx`）:
```typescript
import { Mic, Square } from "lucide-react";

<Button onClick={toggleRecording}>
  {isRecording ? <Square /> : <Mic />}
</Button>
```

3. **处理识别结果**:
```typescript
ws.onmessage = (event) => {
  const result = event.data;
  if (result !== "END" && !result.startsWith("{")) {
    setInput(result);
  }
};
```

## 获取密钥

访问 [讯飞开放平台](https://console.xfyun.cn/services/cbf) 申请：
1. 注册/登录账号
2. 创建应用
3. 开通实时语音转写服务
4. 获取 AppID、API Key、API Secret

## 相关文件

| 文件 | 说明 |
|------|------|
| `service/API/api_asr.py` | ASR 服务主文件 |
| `service/utils/audio_processor.py` | 音频格式转换工具 |
| `service/api_server.py` | 后端 API 服务器 |
| `tts_service.py` | TTS 服务（文字转语音）|
| `Frontend/app/components/pre-diagnosis-page.tsx` | 前端集成示例 |
| `Frontend/lib/env.ts` | 环境变量配置 |

## 许可证

本服务基于讯飞开放平台 API，使用前请确保已获得相应授权。
