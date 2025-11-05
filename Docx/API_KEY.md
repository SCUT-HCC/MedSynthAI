根据您提供的信息，我为您拟定以下网站公告：

测试命令如下：
curl http://110.42.53.85:11081/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-qRWFmpfAoJ8Qo72JF0726f0bA1174a5aBbF0D92e4418B511" \
  -d '{
    "model": "deepseek-chat",
    "messages": [
      {
        "role": "user",
        "content": "你好，请用中文介绍一下你自己。"
      }
    ]
  }'
---

## 📢 网站公告

### 🔗 API 调用地址

本站提供标准 OpenAI 格式的 API 接口，请在您的应用中配置以下信息：

**API Base URL：** `http://110.42.53.85:11081/v1`

**使用说明：**
- 请在本站用户中心生成您的专属 API Key（令牌）
- 在调用时将 API Key 填入 `Authorization` 请求头
- 支持所有兼容 OpenAI SDK 的客户端和应用

**配置示例（Python）：**
```python
from openai import OpenAI

client = OpenAI(
    api_key="sk-xxxxxx",  # 替换为您的令牌
    base_url="http://110.42.53.85:11081/v1"
)
```

---

### 🤖 可用模型列表

本站已接入以下高性能大语言模型，可根据您的需求选择使用：

#### **阿里通义千问系列**
- `qwen-max` - 旗舰模型，适合复杂任务
- `qwen3-plus` - 均衡模型，性价比高
- `qwen3-coder-plus` - 专业代码模型
- `qwen3-vl-plus` - 多模态视觉理解模型

#### **DeepSeek 系列**
- `deepseek-chat` - 高性价比对话模型
- `deepseek-reasoner` - 推理增强模型，支持深度思考

#### **MiniMax 系列**
- `abab6.5s-chat` - 超长文本处理模型

#### **智谱 GLM 系列**
- `glm-4.6` - 国产顶尖编程模型

---

### 📌 温馨提示

1. 所有模型均支持流式输出和非流式输出
2. 部分模型支持多模态输入（图片、文本）
3. 建议根据任务类型选择合适的模型以获得最佳效果
4. 如有问题请联系客服或查看使用文档

**祝您使用愉快！** 🎉

---

这个公告清晰地列出了 API 地址和可用模型，没有提及价格信息。您可以根据实际情况调整内容或格式！