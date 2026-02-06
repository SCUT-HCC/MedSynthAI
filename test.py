import requests
import json
import sys

# API 基础地址
BASE_URL = "http://127.0.0.0:8000"
BASE_URL = "http://localhost:8000"
CHAT_URL = f"{BASE_URL}/api/chat"
REPORT_URL = f"{BASE_URL}/dialogue/report"

def get_report(session_id):
    """调用报告接口并打印"""
    if not session_id:
        return

    print(f"\n[系统] 正在获取病历报告 (Session ID: {session_id})...")
    try:
        # 发送 GET 请求，参数为 session_id
        response = requests.get(REPORT_URL, params={"session_id": session_id})
        response.raise_for_status()
        report = response.json()
        
        print("\n" + "="*30)
        print("       最终病历报告")
        print("="*30)
        print(f"分诊结果: {report.get('分诊结果')}")
        print(f"主诉:     {report.get('主诉')}")
        print(f"现病史:   {report.get('现病史')}")
        print(f"既往史:   {report.get('既往史')}")
        print("="*30 + "\n")
        
    except Exception as e:
        print(f"[错误] 获取报告失败: {e}")

def run_chat():
    print("=== MedSynthAI API 测试客户端 ===")
    print("输入 'exit' 或 'q' 退出并查看报告")
    
    session_id = ""
    
    # 1. 第一轮交互
    first_msg = input("\n[患者] 请输入第一句话 (例如: 医生你好，我头痛): ")
    if first_msg.lower() in ['exit', 'q']:
        return

    payload = {
        "session_id": "",
        "patient_content": first_msg
    }
    
    try:
        print("正在请求 API...")
        response = requests.post(CHAT_URL, json=payload)
        response.raise_for_status()
        data = response.json()
        
        session_id = data["session_id"]
        print(f"\n[医生] {data['worker_inquiry']}")
        
        # 2. 后续交互循环
        while not data.get("is_completed", False):
            user_input = input("\n[患者] > ")
            if user_input.lower() in ['exit', 'q']:
                break
                
            payload = {
                "session_id": session_id,
                "patient_content": user_input
            }
            
            response = requests.post(CHAT_URL, json=payload)
            response.raise_for_status()
            data = response.json()
            
            print(f"\n[医生] {data['worker_inquiry']}")
            
            if data.get("is_completed"):
                print("\n=== 问诊结束 ===")
                break
                
    except Exception as e:
        print(f"\n发生错误: {e}")
        if 'response' in locals():
            print(f"服务器响应: {response.text}")
    finally:
        # 无论正常结束还是用户退出，都尝试获取报告
        if session_id:
            get_report(session_id)

if __name__ == "__main__":
    run_chat()