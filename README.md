# MedSynthAI - 智能医疗问诊模拟系统

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![Node.js](https://img.shields.io/badge/Node.js-18+-green.svg)](https://nodejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-teal.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-15-black.svg)](https://nextjs.org/)
[![License](https://img.shields.io/badge/License-Academic-orange.svg)](LICENSE)

**基于大语言模型的多智能体医疗诊断模拟平台**

[功能特性](#功能特性) • [快速开始](#快速开始) • [使用指南](#使用指南) • [API文档](#api文档)

</div>

---

## 目录

- [项目概述](#项目概述)
- [功能特性](#功能特性)
- [技术架构](#技术架构)
- [目录结构](#目录结构)
- [快速开始](#快速开始)
- [使用指南](#使用指南)
- [API文档](#api文档)
- [开发规范](#开发规范)
- [贡献指南](#贡献指南)
- [故障排查](#故障排查)
- [许可证](#许可证)

---

## 项目概述

MedSynthAI 是一个基于大型语言模型（LLM）的先进医疗诊断模拟平台。通过构建一个由**8个专业智能体（Agent）**组成的协作系统，精准模拟真实医生从接诊、分诊到病史采集的完整诊断流程。

### 双模式设计

| 模式 | 适用场景 | 核心功能 |
|------|----------|----------|
| **科研模式** | 算法研究、批量评估 | 并行处理大规模病例，生成可复现的性能评估报告 |
| **工程模式** | 实际应用、Web交互 | 提供完整的Web应用，支持实时多轮对话问诊 |

### 核心工作流

```
患者主诉 → 接诊分析 → 智能分诊 → 任务监控 → 规划提问 → 深入询问 → 评估完成 → 生成报告
   ↓           ↓          ↓          ↓          ↓          ↓          ↓          ↓
 Recipient  Triage    Monitor  Controller  Prompter  Inquirer  Evaluator  报告
```

---

## 功能特性

### 核心能力

- **🤖 8个专业Agent协作**
  - 虚拟病人模拟、初步接诊、智能分诊、任务监控
  - 流程控制、提问优化、专业询问、多维评估

- **📊 三阶段诊断流程**
  - 分诊阶段（≤4轮）：快速确定重点方向
  - 现病史阶段：深入挖掘疾病细节
  - 既往史阶段：全面收集历史健康信息

- **🎯 多维度评估体系**
  - 临床问诊能力、沟通表达能力、信息收集全面性
  - 与标准病历的相似度对比（主诉、现病史、既往史）

### 语音交互功能

#### 🎤 ASR - 语音识别（Speech to Text）

- 基于讯飞开放平台实时语音转写API
- 支持流式识别结果返回
- 自动音频格式转换（webm → PCM）
- WebSocket实时双向通信

#### 🔊 TTS - 语音合成（Text to Speech）

- 基于讯飞开放平台语音合成API
- 多种发音人（晓燕、晓峰、晓美、晓琪）
- 可调节语速、音量、音高
- 支持多种音频格式（MP3、PCM、Speex）

---

## 技术架构

### 后端技术栈

| 组件 | 技术选型 | 说明 |
|------|----------|------|
| **核心框架** | Python 3.12+ | 主要开发语言 |
| **Web框架** | FastAPI | 高性能异步Web框架 |
| **数据库** | PostgreSQL | 数据持久化 |
| **LLM接口** | DeepSeek / 通义千问 | 支持多种大模型 |
| **语音服务** | 讯飞开放平台 | ASR + TTS |

### 前端技术栈

| 组件 | 技术选型 | 说明 |
|------|----------|------|
| **框架** | Next.js 15 (App Router) | React框架 |
| **UI库** | Shadcn/ui + Tailwind CSS | 现代化UI组件 |
| **语言** | TypeScript | 类型安全 |
| **状态管理** | React Hooks | 内置状态管理 |

### 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        用户界面层                             │
│              Next.js Frontend (Port 3000)                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  预诊页面 | 聊天组件 | 录音按钮 | 语音播放           │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓ WebSocket/HTTP
┌─────────────────────────────────────────────────────────────┐
│                        服务层                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ API Server   │  │ ASR Service  │  │ TTS Service  │      │
│  │  (Port 8000) │  │  (Port 8000) │  │  (Port 8003) │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                        业务逻辑层                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Agent系统 + 工作流引擎 + 评估模块            │  │
│  │  8个专业Agent | 任务管理 | 流程控制 | 多维度评估     │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                        数据层                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ PostgreSQL   │  │ LLM API      │  │ 讯飞语音API   │      │
│  │  会话/病历    │  │  DeepSeek等  │  │  ASR/TTS     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

---

## 目录结构

```
MedSynthAI/
├── agent_system/              # Agent核心系统
│   ├── base/                  # 基础Agent类和响应模型
│   ├── virtual_patient/       # 虚拟病人Agent
│   ├── recipient/             # 接诊Agent
│   ├── triager/               # 分诊Agent
│   ├── monitor/               # 监控Agent
│   ├── controller/            # 任务控制Agent
│   ├── prompter/              # 提示词Agent
│   ├── inquirer/              # 询问Agent
│   └── evaluator/             # 评估Agent
│
├── data_processing/           # 数据处理模块
│
├── research/                  # 科研模式
│   ├── workflow/              # 完整工作流实现
│   ├── utils/                 # 工具函数集
│   ├── results/               # 实验结果和报告
│   └── main.py                # 科研模式入口
│
├── service/                   # 工程模式（后端服务）
│   ├── api_server.py          # FastAPI主服务（端口8000）
│   ├── main.py                # 终端交互式问诊
│   ├── tts_service.py         # TTS服务（端口8003）
│   ├── API/                   # RESTful接口定义
│   │   ├── api_chat.py        # 聊天交互接口
│   │   ├── api_report.py      # 病历报告接口
│   │   └── api_asr.py         # 语音识别接口
│   ├── Model/                 # 数据模型和数据库交互
│   ├── workflow/              # 实时问诊工作流
│   └── utils/                 # 工具函数
│
├── Frontend/                  # 前端界面（Next.js）
│   ├── app/                   # Next.js App Router
│   │   ├── components/        # React组件
│   │   │   ├── ui/           # Shadcn/ui基础组件
│   │   │   └── pre-diagnosis-page.tsx
│   │   └── lib/              # 工具函数和类型定义
│   ├── public/                # 静态资源
│   ├── package.json           # 依赖配置
│   └── next.config.ts         # Next.js配置
│
├── .env.example               # 环境变量示例
├── requirements.txt           # Python依赖
├── README.md                  # 本文档
└── .gitignore                 # Git忽略配置
```

---

## 快速开始

### 环境要求

- **Python**: 3.12+
- **Node.js**: 18+
- **PostgreSQL**: 14+（工程模式需要）
- **ffmpeg**: 4.0+（语音功能需要）

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd MedSynthAI
```

### 2. 配置环境

**创建并激活Conda环境**

```bash
conda create -n medsynthai python=3.12
conda activate medsynthai
```

**安装Python依赖**

```bash
pip install -r requirements.txt
```

**配置环境变量**

```bash
# 复制示例配置文件
cp .env.example .env

# 编辑.env文件，填入必要的配置
nano .env
```

环境变量配置项：
```bash
# LLM API配置
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat

# 讯飞语音服务配置（可选）
XFYUN_APP_ID=your_app_id
XFYUN_API_KEY=your_api_key
XFYUN_API_SECRET=your_api_secret
```

### 3. 安装系统依赖

**安装ffmpeg（语音功能需要）**

```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Windows
# 下载并安装: https://ffmpeg.org/download.html
```

### 4. 配置前端

```bash
cd Frontend

# 安装Node.js（在当前conda环境）
conda install -c conda-forge nodejs

# 安装npm依赖
npm install

# 返回项目根目录
cd ..
```

---

## 使用指南

### 模式一：科研模式（批量评估）

适用于算法研究和模型评估。

#### 手动运行单个实验

```bash
# 确保激活环境
conda activate medsynthai

# 查看所有可用参数
python research/main.py --help

# 运行实验（使用默认参数）
python research/main.py

# 自定义参数运行
python research/main.py --controller-mode score_driven --dataset-size 100
```

#### 自动化批量实验

```bash
# 赋予执行权限
chmod +x research/research.sh

# 运行自动化实验脚本
bash research/research.sh
```

该脚本将自动运行所有控制器模式，生成：
- 实验结果报告：`results_<date>_<mode>/`
- 性能分析图表：`research/Draw/Figures/`

### 模式二：工程模式（Web应用）

适用于实际应用和交互式问诊。

#### 启动后端服务

**启动主API服务（端口8000）**

```bash
conda activate medsynthai
python service/api_server.py
```

**启动TTS服务（端口8003，可选）**

```bash
# 在另一个终端
python service/tts_service.py
```

#### 启动前端应用

```bash
# 在另一个终端
cd Frontend
npm run dev
```

前端将运行在 `http://localhost:3000`

#### 配置前后端通信

前端默认连接 `http://127.0.0.1:8000`。如需修改：

**场景一：前后端在同一台服务器（默认）**

无需配置，使用默认值即可。

**场景二：前端在本地，后端在远程服务器**

在 `Frontend/` 目录创建 `.env.local`：

```bash
NEXT_PUBLIC_MEDSYNTHAI_FRONTEND_API_HOST=your-server-ip
NEXT_PUBLIC_MEDSYNTHAI_FRONTEND_API_PORT=8000
NEXT_PUBLIC_MEDSYNTHAI_FRONTEND_TTS_PORT=8003
```

#### 访问应用

- 前端界面：`http://localhost:3000`
- 后端API文档：`http://localhost:8000/docs`
- TTS测试页面：`http://localhost:8003/client`

---

## API文档

### 核心API接口

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/chat` | POST | 聊天交互接口 |
| `/dialogue/report` | GET | 获取病历报告 |
| `/docs` | GET | Swagger API文档 |

### ASR服务 - 语音识别

**WebSocket端点**: `ws://localhost:8000/audio/upload`

**连接流程**：
1. 客户端连接WebSocket
2. 服务返回 `{"type": "ready"}`
3. 客户端发送音频数据（webm格式）
4. 服务自动转换为PCM并识别
5. 返回识别文字结果

**请求示例**（JavaScript）：

```javascript
const ws = new WebSocket('ws://localhost:8000/audio/upload');

ws.onopen = () => {
  // 发送音频数据
  ws.send(audioArrayBuffer);
};

ws.onmessage = (event) => {
  const result = event.data;
  if (result !== 'END' && !result.startsWith('{')) {
    console.log('识别结果:', result);
  }
};
```

### TTS服务 - 语音合成

**WebSocket端点**: `ws://localhost:8003/ws/tts`

**连接流程**：
1. 客户端连接WebSocket
2. 服务返回 `{"type": "ready", ...}`
3. 客户端发送合成请求（JSON）
4. 服务返回音频数据（二进制）和状态消息

**请求格式**：

```json
{
  "text": "要转换为语音的文本",
  "voice_name": "xiaoyan",
  "speed": 50,
  "volume": 50,
  "pitch": 50,
  "audio_format": "lame"
}
```

**参数说明**：

| 参数 | 范围 | 默认值 | 说明 |
|------|------|--------|------|
| voice_name | - | xiaoyan | 发音人（xiaoyan/xiaofeng/xiaomei/xiaoqi） |
| speed | 0-100 | 50 | 语速 |
| volume | 0-100 | 50 | 音量 |
| pitch | 0-100 | 50 | 音高 |
| audio_format | lame/raw/speex | lame | 音频格式 |

**请求示例**（JavaScript）：

```javascript
const ws = new WebSocket('ws://localhost:8003/ws/tts');
const audioChunks = [];

ws.onopen = () => {
  ws.send(JSON.stringify({
    text: "你好，欢迎使用语音合成服务",
    voice_name: "xiaoyan",
    audio_format: "lame"
  }));
};

ws.onmessage = (event) => {
  if (event.data instanceof Blob) {
    audioChunks.push(event.data);
  } else {
    const data = JSON.parse(event.data);
    if (data.type === 'complete') {
      // 合成完成，播放音频
      const audioBlob = new Blob(audioChunks, { type: 'audio/mpeg' });
      const audio = new Audio(URL.createObjectURL(audioBlob));
      audio.play();
    }
  }
};
```

### 发音人列表

| voice_name | 名称 | 特点 |
|------------|------|------|
| xiaoyan | 晓燕 | 女声，情感柔和 |
| xiaofeng | 晓峰 | 男声，沉稳大气 |
| xiaomei | 晓美 | 女声，活泼开朗 |
| xiaoqi | 晓琪 | 女声，年轻活力 |

---

## 开发规范

### 代码规范

- **类型注解**：所有方法签名必须包含完整类型注解
- **文档注释**：每个模块、类和方法都需要中文docstring
- **命名规范**：遵循PEP 8，使用有意义的变量名
- **阶段化注释**：复杂逻辑使用注释组织流程

### Git提交规范

遵循 Conventional Commits 规范：

```
<type>(<scope>): <subject>

<body>

<footer>
```

**类型（type）**：
- `feat`: 新功能
- `fix`: Bug修复
- `docs`: 文档更新
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建/工具链相关

**示例**：
```
feat(service): 添加TTS语音合成服务

- 集成讯飞TTS API
- 支持多种发音人和音频格式
- 添加WebSocket端点 /ws/tts

Closes #123
```

---

## 贡献指南

### Pull Request规范

为了保证代码质量和审查效率，请遵循以下规范：

**代码变更限制**：
- 单次PR代码行数 ≤ **300行**
- 修改文件数量 ≤ **5个**
- PR内commit数量 ≤ **3个**
- 一个PR只专注于**一个功能**

**禁止提交的内容**：
- ❌ 个人笔记和任务规划文件
- ❌ 本地配置文件（`.vscode/`, `.idea/`, `.env`）
- ❌ 临时测试文件
- ❌ 个人待办事项

**应该提交的内容**：
- ✅ 功能代码和相应的单元测试
- ✅ 必要的文档更新
- ✅ 配置文件的示例模板（如`.env.example`）
- ✅ 项目相关的通用文档

### 提交前检查清单

- [ ] 代码变更量符合规范（<300行，<5个文件）
- [ ] Commit信息遵循Conventional Commits规范
- [ ] 代码包含完整的类型注解和中文docstring
- [ ] 已移除所有个人笔记和临时文件
- [ ] PR描述清晰说明了改动的目的和实现方式
- [ ] 代码已在本地测试通过
- [ ] 确保`.env`文件不在提交范围内

---

## 故障排查

### 后端服务

#### 问题1：端口被占用

**错误**：`Address already in use`

**解决**：
```bash
# 查找占用进程
lsof -i :8000  # API服务
lsof -i :8003  # TTS服务

# 终止进程
kill -9 <PID>

# 或使用fuser
fuser -k 8000/tcp
```

#### 问题2：数据库连接失败

**检查PostgreSQL服务**：
```bash
# 检查服务状态
sudo systemctl status postgresql

# 启动服务
sudo systemctl start postgresql
```

#### 问题3：LLM API调用失败

**检查配置**：
```bash
# 确认.env文件配置正确
cat .env | grep LLM

# 测试API连接
curl -H "Authorization: Bearer $LLM_API_KEY" $LLM_BASE_URL/models
```

### 前端应用

#### 问题1：模块找不到

**错误**：`Module not found: Can't resolve '@/...'`

**解决**：
```bash
# 检查tsconfig.json中的paths配置
cat Frontend/tsconfig.json | grep -A 5 paths

# 确保有如下配置：
# "paths": {
#   "@/*": ["./*"]
# }
```

#### 问题2：WebSocket连接失败

**可能原因**：
- 后端服务未启动
- CORS配置问题
- 端口号配置错误

**解决**：
```bash
# 检查后端服务
curl http://localhost:8000/

# 检查环境变量配置
cat Frontend/.env.local
```

### 语音服务

#### 问题1：ffmpeg未安装

**错误**：`音频格式转换失败，请确保已安装ffmpeg`

**解决**：
```bash
# 验证安装
ffmpeg -version

# 安装ffmpeg
sudo apt-get install ffmpeg  # Ubuntu/Debian
brew install ffmpeg          # macOS
```

#### 问题2：麦克风权限被拒绝

**错误**：`Permission denied`

**解决**：
- 确保网站使用HTTPS或localhost
- 在浏览器设置中允许麦克风权限
- 检查系统隐私设置

---

## 项目状态

| 模块 | 状态 | 说明 |
|------|------|------|
| 科研模式 | ✅ 完成 | 批量处理、多线程、评估报告 |
| Agent系统 | ✅ 完成 | 8个专业Agent协同工作 |
| 工作流系统 | ✅ 完成 | 完整医疗问诊流程 |
| 后端API | ✅ 完成 | FastAPI服务 |
| 前端界面 | 🟡 开发中 | 核心功能已完成 |
| ASR服务 | ✅ 完成 | 语音识别 |
| TTS服务 | ✅ 完成 | 语音合成 |
| 测试框架 | 🟡 完善中 | 单元测试和集成测试 |

---

## 常见问题

<details>
<summary><b>Q: 科研模式和工程模式有什么区别？</b></summary>

**科研模式**用于批量评估和算法研究，处理数据集生成评估报告。
**工程模式**用于实际应用，提供Web界面支持实时交互式问诊。
</details>

<details>
<summary><b>Q: 如何切换不同的LLM模型？</b></summary>

修改`.env`文件中的配置：
```
LLM_MODEL=deepseek-chat  # 或其他支持的模型
LLM_BASE_URL=https://api.example.com/v1
```
</details>

<details>
<summary><b>Q: ASR和TTS服务必须启动吗？</b></summary>

不是必须的。ASR和TTS是可选的语音交互功能。
- 不启动ASR：无法使用语音输入，但可以使用文字输入
- 不启动TTS：无法听到语音回复，但可以看到文字回复
</details>

<details>
<summary><b>Q: 如何获取讯飞API密钥？</b></summary>

访问[讯飞开放平台](https://console.xfyun.cn/services/cbf)：
1. 注册/登录账号
2. 创建应用
3. 开通实时语音转写（ASR）和语音合成（TTS）服务
4. 获取AppID、API Key、API Secret
</details>

---

## 许可证

本项目用于学术研究目的。

---

## 致谢

- 讯飞开放平台 - 提供语音识别和合成API
- FastAPI - 现代化的Python Web框架
- Next.js - React框架
- DeepSeek - 大语言模型API

---

<div align="center">

**如有问题或建议，欢迎提交Issue或Pull Request**

[返回顶部](#medsynthai---智能医疗问诊模拟系统)

</div>
