from config import API_KEY
import requests
import asyncio
from mistralai import Mistral
from mistralai.models import UserMessage
from aiohttp import ClientSession  # 用于执行 HTTP 请求的异步库

#client = Mistral(api_key=API_KEY)
model = "open-mistral-nemo"
#
#chat_response = client.chat.complete_async(
#    model= model,
#    messages = [
#        {   
#            "role": "user",
#            "content": "How many agents can you access?",
#        },
#    ]
#)
#print(chat_response.choices[0].message.content)


# 代理 ID 字典
agents = {
    'memory': "ag:13e82541:20241025:untitlerecord-model-agent-promptd-agent:ccc270fb",
    'expert': "ag:13e82541:20241025:expert-agent:338569a8",
    'analysis': "ag:13e82541:20241025:analysis-model-agent-prompt:c1d46050",
    'workflow': "ag:13e82541:20241025:master-workflow:7bcaf579"
}

# 异步函数，用于根据任务类型选择合适的代理
async def select_agent(task_type):
    return agents.get(task_type, "default_agent_id")

# 异步函数，用于执行任务并获取响应
async def perform_task(task_type, question):
    agent_id = await select_agent(task_type)  # 异步获取代理 ID
    async with ClientSession() as session:  # 使用 aiohttp 的 ClientSession
        # 构建请求 URL 和参数
        url = f"https://api.mistralai.com/chat/complete"
        params = {
            "model": model,
            "agent_id": agent_id,
            "messages": [{"role": "user", "content": question}]
        }
        # 发送 POST 请求并等待响应
        async with session.post(url, json=params) as response:
            data = await response.json()  # 异步获取 JSON 响应
            return data['choices'][0]['message']['content']  # 解析并返回内容

# 示例用法，定义主异步函数
async def main():
    task_type = 'expert'
    question = "What are the latest trends in AI?"
    response_content = await perform_task(task_type, question)
    print(response_content)

# 运行主函数
if __name__ == "__main__":
    asyncio.run(main())