# MedSynthAI - 智能医疗问诊模拟系统

MedSynthAI 是一个基于大型语言模型（LLM）的先进医疗诊断模拟平台。它通过构建一个由多个专业智能体（Agent）协作的系统，来模拟真实医生从接诊、分诊到病史采集的完整诊断流程。

## 项目概述

项目采用**科研**与**工程**双模式设计，旨在满足不同场景下的需求：

### 科研模式 (Research Mode)

为算法研究设计，支持对大语言模型在医疗诊断任务中的能力进行**批量、可复现的自动化评估**。通过并行处理大规模病例数据，本模式可生成详尽的性能指标与多维度分析报告，为模型迭代与学术探索提供坚实的数据支撑。

### 工程模式 (Service Mode)

为实际应用设计，提供一个**功能完整、可交互的Web应用**。用户能与AI医生进行实时多轮对话，系统后端无缝管理会话、执行诊断逻辑，并持久化存储电子病历，完整展示了项目的落地潜力。

### 核心能力

系统通过一个由 **8 个专业化智能体（Agent）** 组成的协作网络，精准模拟了从接诊、分诊到病史采集的完整医疗问诊流程。各 Agent 职责明确，协同工作，覆盖了**虚拟病人模拟、初步接诊、智能分诊、任务监控、流程控制、提问优化、专业询问、多维评估**等关键环节。

### 工作流程

问诊流程被精心设计为三个关键阶段：**分诊阶段**通过不超过4轮的快速问答确定重点方向；**现病史阶段**深入挖掘疾病细节；**既往史阶段**全面收集历史健康信息。整个流程在最多30步内完成，每一步都经过严谨的子任务处理，确保了问诊的专业性与高效性。

### 评估体系

我们建立了一套多维度、量化的评估框架，从**临床问诊能力、沟通表达能力、信息收集全面性、整体专业性**等角度对AI医生的表现进行综合评分。同时，通过计算与标准病历的**主诉、现病史、既往史相似度**，客观衡量信息收集的准确性。所有维度均采用0-5分制，并附有详细的评价依据与改进建议。

### 核心特性

- **模块化多智能体架构**: 各司其职的 Agent 团队，高度模拟真实医疗协作模式。
- **双模式驱动**: 内置科研与工程两种运行模式，无缝切换，兼顾研究的可复现性与应用的可交互性。
- **可插拔LLM后端**: 支持通过配置灵活切换和扩展不同的大型语言模型（如 DeepSeek, GPT-OSS, GLM），便于进行模型对比实验。
- **动态任务工作流**: 引入分诊、现病史、既往史等诊断阶段，并支持智能、顺序、分数驱动等多种任务控制策略，使问诊过程更具逻辑性和目的性。
- **数据持久化与状态管理**: 工程模式采用 PostgreSQL 存储会话与病历，并利用内存状态机管理工作流，确保服务稳定可靠。
- **完整的前后端实现**: 提供基于 FastAPI 的后端服务和基于 Next.js 的现代化前端界面，构成端到端的AI应用解决方案。

## 技术架构

项目采用分层模块化设计，确保了高内聚、低耦合，其核心组件包括：

- **Agent核心系统 (`agent_system/`)**: 定义所有智能体的基类与核心能力，是整个系统的大脑。
- **工作流模块 (`workflow/`)**: 为科研和工程模式分别实现工作流控制器、单步执行器和任务管理器，负责编排和驱动 Agent 执行流程。
- **模式主入口**:
    - **科研模式 (`research/`)**: 通过 `main.py` 启动，利用多线程并行处理数据集，并由 `utils/` 脚本集负责参数解析、日志记录和报告生成。
    - **工程模式 (`service/`)**: 通过 `api_server.py` 启动，利用 FastAPI 搭建 RESTful API 服务，其中 `API/` 目录定义接口，`Model/` 目录负责数据库交互。
- **前端 (`MedSynthAI-Frontend/`)**: 一个独立的 Next.js 项目，通过调用后端 API 实现用户交互。


## 目录结构

```
MedSynthAI/
├── agent_system/          # Agent核心系统
│   ├── base/              # 基础Agent类和响应模型
│   ├── virtual_patient/   # 虚拟病人Agent
│   ├── recipient/         # 接诊Agent
│   ├── triager/           # 分诊Agent
│   ├── monitor/           # 监控Agent
│   ├── controller/        # 任务控制Agent
│   ├── prompter/          # 提示词Agent
│   ├── inquirer/          # 询问Agent
│   └── evaluator/         # 评估Agent
|   
├── data_processing /      # 数据处理模块
│   ├── iiyi_crawl4ai_kewords.py     #数据处理代码
│
├── research/              # 科研模式
│   ├── workflow/          # 完整工作流实现
│       ├── medical_workflow.py    # 主工作流控制器
│           ├── task_manager.py        # 任务阶段管理
│           ├── step_executor.py       # 步骤执行器
│           └── workflow_logger.py     # 日志记录
|   ├── Drawing /                      #绘图代码文件
│   └── results/
│       ├── batch_report_YYYYMMDD_HHMMSS.json    # 详细的JSON格式报告
│       ├── batch_summary_YYYYMMDD_HHMMSS.txt    # 人类可读的摘要报告
│       └── logs/                                # 详细的处理日志
│           ├── workflow_0001_case_XXXX.jsonl    # 每个病例的处理日志
            └── batch_processing_YYYYMMDD_HHMMSS.log  # 批处理系统日志
    ├── utils/                          # 工具函数
        ├── parse_arguments.py          # 命令行参数解析
        ├── setup_logging.py            # 日志系统设置
        ├── load_dataset.py             # 数据集加载与切分
        ├── is_case_completed.py        # 检查病例是否已处理，支持断点续跑
        ├── run_workflow_batch.py       # 批量处理主逻辑
        ├── process_single_sample.py    # 单一样本处理逻辑
        ├── update_progress.py          # 线程安全的进度更新器
        ├── print_progress_report.py    # 打印实时进度报告
        └── generate_summary_report.py  # 生成最终的摘要和详细报告
    ├── main.py                         # 科研模式主函数
    ├── config.py                       # 模型配置文件
│
├── service/               # 工程模式
│   ├── api_server.py      # FastAPI 应用主入口
│   ├── main.py            # 终端交互式问诊主函数
│   ├── API/               # RESTful接口定义
│   │   ├── api_chat.py    # 聊天交互接口
│   │   └── api_report.py  # 病历报告接口
│   ├── Model/             # Pydantic数据模型和数据库交互
│   │   ├── base.py        # 数据库基类 (PostgreSQL)
│   │   ├── Chat.py        # 聊天数据模型
│   │   └── report.py      # 报告数据模型
│   ├── workflow/          # 实时问诊工作流
│   │   ├── medical_workflow.py # 工作流主控制器
│   │   ├── step_executor.py    # 单步执行器
│   │   ├── task_manager.py     # 任务管理器
│   │   └── workflow_logger.py  # 轻量级日志记录器
│  
├── Frontend/ # 前端界面 (Next.js App) 
│   ├── app/ # Next.js App Router 核心目录 
        ├── lib/ # 全局工具函数 (如 env.ts) 
        ├── pre-triage/ # 预分诊/问诊核心功能模块
            ├── components/ # 预分诊模块的React组件  
                ├── ui/ # Shadcn/ui 基础组件 (Button, Input等) 
                ├── message.tsx # 聊天消息组件 
                └── pre-diagnosis-page.tsx # 预分诊主页面组件 
            ├── lib/ # 模块专属工具函数和类型定义 
            ├── styles/ # 模块专属样式文件 
            ├── layout.tsx # 预分诊模块布局 
            └── page.tsx # 预分诊模块入口页面 
        ├── public/ # 静态资源 (图片, SVG等) 
        ├── globals.css # 全局CSS样式 
        ├── layout.tsx # 应用根布局 
        └── page.tsx # 应用根页面 
    ├── .gitea/ # Gitea CI/CD 工作流配置 
    ├── Dockerfile # 前端应用的容器化配置 
    ├── next.config.ts # Next.js 配置文件 
    ├── package.json # 项目依赖与脚本 
    ├── tailwind.config.ts # Tailwind CSS 配置文件 
    └── tsconfig.json # TypeScript 配置文件 ```
```

## 系统核心流程解析

无论是科研模式还是工程模式，系统都遵循一个精心设计的诊断工作流。这个流程的意义在于**将一个复杂、开放的医疗诊断任务，拆解为一系列结构化、可度量的子任务**，从而引导LLM逐步、有逻辑地完成信息采集。

1.  **启动与初始化**: 工作流启动，任务管理器 (`TaskManager`) 初始化所有诊断任务（分诊、现病史、既往史等），初始完成度均为0。
2.  **接收病人主诉**:
    - **科研模式**: 从数据集中读取虚拟病人的主诉。
    - **工程模式**: 从前端接收用户的第一次输入。
3.  **信息初步处理 (Recipient Agent)**: 接诊智能体对病人的主诉进行分析，提取初步的主诉、现病史和既往史信息。
4.  **分诊 (Triage Agent)**: 分诊智能体根据初步信息，判断患者可能属于的一级和二级科室。这是后续针对性提问的基础。
5.  **任务状态监控 (Monitor Agent)**: 监控智能体评估当前收集到的信息是否足以完成各个子任务（如“发病情况”、“伴随症状”等），并为每个子任务打分。
6.  **任务规划 (Controller Agent)**: 控制器根据监控智能体的评分和预设策略（如`score_driven`模式会优先选择得分最低的任务），决定下一步的提问重点。
7.  **生成问题 (Prompter & Inquirer Agent)**: 提示词智能体根据控制器的指令生成具体的提问Prompt，然后由询问智能体调用LLM，向病人提出一个清晰、专业的问题。
8.  **循环与迭代**: 系统将AI医生的提问返回给用户（或虚拟病人），接收新的回答，然后重复步骤3-7。每一轮对话，系统都会收集更多信息，并持续更新各子任务的完成度分数。
9.  **结束诊断**: 当任务管理器 (`TaskManager`) 判断所有关键任务的完成度都达到预设阈值（如85%），或者达到最大对话轮次时，工作流结束。
10. **生成报告**:
    - **科研模式**: 生成包含完整对话、最终诊断摘要和各项评估指标的JSON报告。
    - **工程模式**: 将最终的病历（主诉、现病史、既往史、分诊结果）存入数据库，前端可随时查询。

## 快速开始

### 1. 环境准备

- **Python**: 推荐 `3.12+`
- **Conda**: 用于管理Python环境。
- **Node.js**: 用于运行前端项目。
- **SQLITE**: 工程模式需要使用的数据库。请确保已安装并正在运行。

### 2. 安装与配置

**克隆项目**
```bash
git clone <your-repo-url>
cd MedSynthAI
```

**创建虚拟环境**
```bash
# 1. 创建并激活Conda环境
conda create -n medsynthai python=3.12
# 激活虚拟环境
conda activate medsynthai

# 2. 安装Python依赖
pip install -r requirements.txt
```

**配置后端**
```bash
# 1. 配置环境变量
# 复制示例文件
cp .env.example .env
# 编辑.env文件，填入你的LLM API Key和Base URL
a、运行 nano .env 
b、或者直接打开.env文件替换填入你的LLM API Key和Base URL

```

**配置前端**
```bash
# 切换到前端目录
cd Frontend

#在当前 conda 环境安装 node（保持环境一致）
conda install -c conda-forge nodejs

# 验证
node -v
npm -v

# 安装models
npm install
```

### 3. 运行系统

#### 3.1 模式一：科研模式 (批量评估)

**3.1.1 手动运行单个实验**:
如果您想手动运行，需要先进行参数配置。
a、你可以使用 `python research/main.py --help` 查看所有可用参数，并在research/utils/parse_arguments.py选择对应参数的修改
b、或者在research/utils/parse_arguments.py查看选择对应参数的修改。

参数配置后可以直接通过以下命令运行
```bash
python research/main.py
```

**3.1.2 支持自动化运行实验**:
科研模式设计用于自动化运行实验。`research/research.sh` 脚本是完成此任务的核心。

**3.1.3 自动化运行所有实验**:
该脚本将自动为 `normal`, `sequence`, `score_driven` 三种控制器模式分别运行批处理，并将结果保存在带时间戳和模式名的独立目录中，最后调用绘图脚本生成所有分析图表。

```bash
# 确保先激活虚拟环境
conda activate medsynthai

# 确保脚本有执行权限
chmod +x research/research.sh

# 运行自动化实验脚本
bash research/research.sh
```
实验结果（日志、报告）和图表将分别保存在 `results_<date>_*` 和 `research/Draw/Figures/` 目录下。



#### 3.2 模式二：工程模式 (Web应用)

工程模式需要同时启动后端服务和前端应用。

**0. 准备工作**
'''bash

'''

**1. 启动后端 (FastAPI)**
```bash
# 确保在项目根目录 (MedSynthAI/) 并已激活Conda环境
conda activate medsynthai

# 启动API服务器
python service/api_server.py
```


```bash
# 如果出现错误：ERROR:    [Errno 98] error while attempting to bind on address ('0.0.0.0', 8000): address already in use
lsof -i :8000
# 终止进程(使用上一步找到的 PID),例如：
kill -9 xxxxxx
#重新运行服务
python service/api_server.py
```


服务将运行在 `http://0.0.0.0:8000`。

**2. 启动前端 (Next.js)**
```bash
# 打开一个新的终端，切换到前端目录
cd Frontend
```
**确保已经进行相关库安装**

```bash

# 验证
node -v
npm -v

```

**配置前端-后端通信地址**

前端应用需要知道后端API服务器的地址才能正确发送请求。此配置由环境变量控制，并有默认值。

配置文件位于 `Frontend/lib/env.ts`，其中定义了API地址的构成：
```typescript
export const API_HOST = process.env.NEXT_PUBLIC_MEDSYNTHAI_FRONTEND_API_HOST || '127.0.0.1';
export const API_PORT = process.env.NEXT_PUBLIC_MEDSYNTHAI_FRONTEND_API_PORT || '8000';
export const API_BASE_URL = `http://${API_HOST}:${API_PORT}`;
```

**如何修改**

最佳实践是**不要直接修改 `env.ts` 文件**，而是通过在前端项目根目录 (`Frontend/`) 创建一个 `.env.local` 文件来覆盖默认值。

**场景一：前后端都在同一台服务器上运行（默认情况）**

- **说明**: 这是最常见的情况，前端和后端都在同一台机器上。
- **配置**: 您**无需任何额外配置**。系统默认使用 `127.0.0.1` 作为主机地址，`8000` 作为端口号，这正是服务器内部通信所需要的。
- **最终API地址**: `http://127.0.0.1:8000`

**场景二：前端在本地开发，后端在远程服务器上**

- **说明**: 您在自己的电脑上开发前端，但需要连接到一台远程服务器上的后端API。
- **配置**:
    1. 在 `Frontend/` 目录下创建一个名为 `.env.local` 的文件。
    2. 在该文件中添加以下内容，将 `your-remote-server-ip` 替换为您服务器的公网IP地址：
       ```
       NEXT_PUBLIC_MEDSYNTHAI_FRONTEND_API_HOST=your-remote-server-ip
       ```
       如果后端端口不是8000，您也可以通过 `NEXT_PUBLIC_MEDSYNTHAI_FRONTEND_API_PORT` 变量来指定。
- **最终API地址**: `http://your-remote-server-ip:8000`

完成配置后，重新启动前端开发服务器即可生效。

```

**启动开发服务器**
```bash
npm run dev
```
前端应用将运行在 `http://localhost:3000`。

现在，您可以在浏览器中打开 `http://localhost:3000`，开始与AI医生进行交互式问诊。

## 运行系统
### 科研模式

科研模式用于对整个数据集进行批量自动化评估。系统支持三种不同的任务控制模式，通过 --controller-mode 参数进行切换，以满足不同的研究需求。

### 工程模式

## 开发规范

本项目遵循严格的研究型代码开发规范。所有方法签名必须包含完整的类型注解，确保代码的可读性和类型安全。每个模块、类和方法都需要提供详细的中文docstring，说明功能、参数、返回值和关键实现细节。遵循YAGNI原则，避免过早抽象和添加不必要的功能。使用阶段化注释组织复杂逻辑流程，提高代码的可维护性。

代码提交遵循Conventional Commits规范，使用feat、fix、docs、refactor等前缀清晰标识变更类型。所有提交信息应简洁专业，不包含AI工具署名或生成标识。

## 贡献指南

### Pull Request 规范

为了保证代码质量和审查效率，请遵循以下 PR 提交规范：

**代码变更限制**：
- 单次 PR 修改代码行数不超过 **300 行**
- 修改文件数量建议不超过 **5 个文件**
- PR 内部的 commit 数量应少于 **3 个**
- 一个 PR 只专注于 **一个功能** 或修复

**拆分建议**：
如果你的改动较大，请按照功能逻辑进行拆分，例如：
- PR #1: 添加 guidance 并修改 workflow
- PR #2: 添加 API 接口
- PR #3: 文档更新

### 内容规范

**禁止提交的内容**：
- ❌ 个人笔记和任务规划文件
- ❌ 本地配置文件（如 `.vscode/`, `.idea/`）
- ❌ 临时测试文件
- ❌ 个人待办事项（TODO lists）
- ❌ 学习笔记或个人总结

**应该提交的内容**：
- ✅ 功能代码和相应的单元测试
- ✅ 必要的文档更新
- ✅ 配置文件的示例模板（如 `config.example.yaml`）
- ✅ 项目相关的通用文档

### 提交前检查清单

在提交 PR 之前，请确认：

1. 代码变更量符合规范（<300 行，<5 个文件）
2. Commit 信息遵循 Conventional Commits 规范
3. 代码包含完整的类型注解和中文 docstring
4. 已移除所有个人笔记和临时文件
5. PR 描述清晰说明了改动的目的和实现方式
6. 代码已在本地测试通过

## 贡献指南

### Pull Request 规范

为了保证代码质量和审查效率，请遵循以下 PR 提交规范：

**代码变更限制**：
- 单次 PR 修改代码行数不超过 **300 行**
- 修改文件数量建议不超过 **5 个文件**
- PR 内部的 commit 数量应少于 **3 个**
- 一个 PR 只专注于 **一个功能** 或修复

**拆分建议**：
如果你的改动较大，请按照功能逻辑进行拆分，例如：
- PR #1: 添加 guidance 并修改 workflow
- PR #2: 添加 API 接口
- PR #3: 文档更新

### 内容规范

**禁止提交的内容**：
- ❌ 个人笔记和任务规划文件
- ❌ 本地配置文件（如 `.vscode/`, `.idea/`）
- ❌ 临时测试文件
- ❌ 个人待办事项（TODO lists）
- ❌ 学习笔记或个人总结

**应该提交的内容**：
- ✅ 功能代码和相应的单元测试
- ✅ 必要的文档更新
- ✅ 配置文件的示例模板（如 `config.example.yaml`）
- ✅ 项目相关的通用文档

### 提交前检查清单

在提交 PR 之前，请确认：

1. 代码变更量符合规范（<300 行，<5 个文件）
2. Commit 信息遵循 Conventional Commits 规范
3. 代码包含完整的类型注解和中文 docstring
4. 已移除所有个人笔记和临时文件
5. PR 描述清晰说明了改动的目的和实现方式
6. 代码已在本地测试通过
7. 确保.env 文件不在提交范围内

## 项目状态

### 当前状态：

项目状态

✅ 科研模式: 功能已完全实现，包括批量处理、多线程、日志记录和评估报告生成。
✅ 核心Agent系统: 8个专业化Agent已完成并协同工作。
✅ 工作流系统: 已实现完整的医疗问诊流程模拟。
🟡 工程模式: 正在开发中。后端API服务已基本可用，前端交互界面正在构建。
🟡 测试框架: 已初步建立，正在持续完善单元测试和集成测试。
✅ 配置管理: 已支持通过环境变量和配置文件进行灵活配置。

## 技术选型

### 后端
核心框架: Python 3.12, Pydantic v2
Web框架: FastAPI
数据库: PostgreSQL
LLM接口: 支持 DeepSeek, 阿里通义千问 (GPT-OSS) 等

### 前端

框架: Next.js (App Router), React
UI: Tailwind CSS, Shadcn/ui
语言: TypeScript

## 许可证

本项目用于学术研究目的。
