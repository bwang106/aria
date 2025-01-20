from config import API_KEY
import asyncio
from localStoragePy import localStoragePy
from mistralai import Mistral
from aiohttp import ClientSession

# 初始化 Mistral 客户端
client = Mistral(api_key=API_KEY)
model = "open-mistral-nemo"

# 初始化本地存储
local_storage = localStoragePy('example.mistral_app', 'json')

## 从本地存储获取或设置 API 密钥
#api_key = local_storage.getItem('API_KEY')
#if not api_key:
#    api_key = API_KEY
#    local_storage.setItem('API_KEY', api_key)

# 保存物品信息到本地存储
#def save_item(what, where, status, timestamp):
#    item = {
#        "what": what,
#        "where": where,
#        "status": status,
#        "timestamp": timestamp
#    }
#    local_storage.setItem(what, item)  # 使用物品名称作为键
#
#def get_item(what):
#    return local_storage.getItem(what)

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
    agent_id = await select_agent(task_type)

#    item = get_item(what)
#    if item:
#        print(f"current status of {what}: {item['status']}")
#        if item['status'] == 'available':
#            save_item(what, where, 'unavailable', timestamp)
#            return f"{what} is now unavailable."
#        else:
#            return f"{what} is already unavailable."
        
    async with ClientSession() as session:
        url = "https://api.mistral.ai/v1/agents/completions"
        headers = {'Authorization' : f'Bearer {API_KEY}'}#添加请求头
        params = {
            #"model": model, #这里不需要设置model "msg":"Assertion failed, model can't be set when using an agent"
            "agent_id": agent_id,
            "messages": [{"role": "user", "content": question}]
        }
        async with session.post(url, json=params, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                if 'choices' in data:
                    # 保存物品信息到本地存储
#                    save_item(what, where, 'unavailable', timestamp)
                    return data['choices'][0]['message']['content']
                else:
                    return "No choices available in response."
            else:
                error_data = await response.text()#获取错误信息
                print(f"Failed to fetch data: {response.status}{error_data}:")#打印错误信息
                return f"Failed to fetch data: {response.status}"

# 示例用法，定义主异步函数
async def main():
    task_type = 'workflow'
    question = "I have put the drilling machine in the storage room on the desk1 after use. remember it."
    response_content = await perform_task(task_type, question)
    print(response_content)



# 运行主函数
if __name__ == "__main__":
    asyncio.run(main())