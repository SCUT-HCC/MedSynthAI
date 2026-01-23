"""
MedSynthAI 后端 API 服务入口

该模块负责：
- 创建 FastAPI 应用并配置 CORS 跨域策略
- 注册业务路由（聊天与报告）
- 提供健康检查接口用于基础可用性与跨域验证

注意：
- CORS 允许来源需与前端实际来源完全匹配（协议/域名/端口）。
- 仅在需要时开放 `allow_credentials`，并避免与 `*` 通配符同时使用。
"""

import os
import sys
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict

# --- 环境路径设置 ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
    print(f"项目根目录: {PROJECT_ROOT}")

# 导入路由
# 注意：确保 api_chat.py 和 api_report.py 文件保存无误
from service.API.api_chat import router as chat_router
from service.API.api_report import router as report_router

# --- FastAPI 应用定义 ---
# 只定义一次 app
app = FastAPI(title="MedSynthAI Inquiry API")

# 1. 配置 CORS
# 允许所有来源，方便开发和测试
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=False, # 设为 False 以兼容 allow_origins=["*"]
    allow_methods=["*"],  # 允许所有方法
    allow_headers=["*"],  # 允许所有请求头
)
print(f"[CORS] 允许所有来源")

# 2. 注册路由
# 显式打印，确保执行
print("正在注册路由: /api/chat ...")
app.include_router(chat_router)
app.include_router(report_router)

@app.get("/health")
def health_check() -> Dict[str, str]:
    """
    健康检查接口

    用途：
    - 快速验证服务是否运行正常
    - 联调时用于验证跨域响应头（浏览器或前端直接调用）

    返回：
    - 包含服务状态的字典，如 {"status": "ok"}
    """
    return {"status": "ok"}

# 3. 启动服务
if __name__ == "__main__":
    print("启动 MedSynthAI API 服务...")
    
    # [调试] 打印所有已注册的路由
    print("\n[DEBUG] 已注册的路由列表:")
    for route in app.routes:
        methods = getattr(route, "methods", None)
        print(f"  - Path: {route.path:<20} | Methods: {methods}")
    print("-" * 50 + "\n")

    # 运行服务
    uvicorn.run(app, host="0.0.0.0", port=8000)