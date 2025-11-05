import sys
from openai import OpenAI, APIConnectionError, AuthenticationError

try:
    # 从 config.py 导入 LLM 配置
    from config import LLM_CONFIG
except ImportError:
    print("错误：无法从 config.py 导入 LLM_CONFIG。")
    print("请确保 test_llm.py 和 config.py 在同一个目录下。")
    sys.exit(1)

def test_model(model_key: str):
    """
    测试 LLM_CONFIG 中指定的模型配置。

    Args:
        model_key: LLM_CONFIG 字典中的键名，例如 "deepseek-chat"。
    """
    print(f"--- 正在测试模型: {model_key} ---")

    # 从配置中获取模型信息
    config = LLM_CONFIG.get(model_key)
    if not config:
        print(f"错误: 在 LLM_CONFIG 中未找到 '{model_key}' 的配置。")
        return

    params = config.get("params", {})
    api_key = params.get("api_key")
    base_url = params.get("base_url")
    model_id = params.get("id")

    if not all([api_key, base_url, model_id]):
        print("错误: 配置中缺少 api_key, base_url 或 id。")
        return

    print(f"模型 ID: {model_id}")
    print(f"Base URL: {base_url}")

    try:
        # 初始化 OpenAI 客户端
        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )

        # 发送测试请求
        print("\n正在向模型发送请求...")
        chat_completion = client.chat.completions.create(
            model=model_id,
            messages=[
                {
                    "role": "user",
                    "content": "你好，请用中文做一个简单的自我介绍。",
                }
            ],
            stream=False,  # 为了简单测试，不使用流式输出
        )

        # 打印模型的回复
        response_content = chat_completion.choices[0].message.content
        print("\n✅ 模型回复成功:")
        print(response_content)

    except AuthenticationError:
        print("\n❌ 测试失败: 身份验证错误。请检查您的 API_KEY 是否正确且有效。")
    except APIConnectionError as e:
        print(f"\n❌ 测试失败: 无法连接到 API 服务器。请检查您的 BASE_URL 是否正确，以及网络连接是否正常。")
        print(f"错误详情: {e.__cause__}")
    except Exception as e:
        print(f"\n❌ 测试失败: 发生未知错误。")
        print(f"错误详情: {e}")
    finally:
        print("-" * (len(model_key) + 20))


if __name__ == "__main__":
    # 在这里指定要测试的模型键名
    test_model("deepseek-chat")
