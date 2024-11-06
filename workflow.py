from config import API_KEY
import asyncio
from localStoragePy import localStoragePy
from mistralai import Mistral
from aiohttp import ClientSession
import re
import logging

logging.basicConfig(filename='workflow.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 初始化 Mistral 客户端
client = Mistral(api_key=API_KEY)
model = "open-mistral-nemo"

# 代理 ID 字典
agents = {
    'memory': "ag:13e82541:20241025:untitlerecord-model-agent-promptd-agent:ccc270fb",
    'expert': "ag:13e82541:20241025:expert-agent:338569a8",
    'analysis': "ag:13e82541:20241025:analysis-model-agent-prompt:c1d46050",
    'workflow': "ag:13e82541:20241025:master-workflow:7bcaf579"
}

central_database = {} 

class AgentWorkflow:
    def __init__(self):
        self.client_session = ClientSession()
        
    async def close(self):
        """关闭资源，确保客户端会话被正确关闭"""
        await self.client_session.close()

    async def perform_task(self, agent_id, question):
        """异步执行任务并获取响应"""
        url = f"https://api.mistral.ai/v1/agents/completions"
        headers = {'Authorization': f'Bearer {API_KEY}'}
        params = {
            "agent_id": agent_id,
            "messages": [{"role": "user", "content": question}]
        }
        async with self.client_session.post(url, json=params, headers=headers) as response:
            data = await response.json()
            logging.info(f"Response from {agent_id}: data: {data}")
            if 'choices' in data and data['choices']:
                return data['choices'][0]['message']['content']
            else:
                logging.error(f"Unexpected response format: {data}")
                raise ValueError("Invalid response format from API.")

    #async def run_workflow_agent(self, query):
    #    """运行工作流代理并返回响应"""
    #    print("### Run Workflow agent")
    #    try:
    #        response = await self.perform_task(agents['workflow'], query)
    #        return response
    #    except Exception as e:
    #        print(f"Request failed: {e}. Please check your request.")
    #        return None



    #def extract_pattern(self, text, pattern):
    #    """从文本中提取模式"""
    #    match = re.search(pattern, text, flags=re.DOTALL)
    #    if match:
    #        return match.group(1).strip()
    #    return None

    async def run_expert_agent(self, query_expert):
        """运行专家代理并返回结果"""
        print("### Run Expert agent")
        logging.info("### Run Expert agent")
        result=await self.perform_task(agents['expert'], query_expert)
        central_database['expert_data'] = result #将结果存储在中央数据库中
        #return await perform_task(agents['expert'], query_expert)
        return result
        
    """query = 
    ### Master Workflow Comprehensive Description

    #### Objective:
    You as the Master Workflow is meticulously designed to orchestrate and synchronize the operations of three pivotal agents: the Expert Agent, the Memory Model Agent, and the Analysis Model Agent. Serving as the central hub, this workflow initiates, coordinates, and monitors the tasks assigned to each agent, ensuring a seamless execution of the entire process flow and enhancing the overall operational efficiency of the organization.

    #### Components:
    1. **Expert Agent**:
       - **Role:** This agent is responsible for capturing and cataloging detailed operational procedures and expert insights, forming the foundational data layer for subsequent analysis.
       - **Trigger:** It is automatically initiated at the start of the workflow or upon detection of specified events, ensuring timely data collection.
       - **Output:** Produces detailed operational data that serves as the primary input for the Memory Model Agent.
        - API: ag:13e82541:20241025:expert-agent:338569a8

    2. **Memory Model Agent**:
       - **Role:** Focuses on logging and tracking critical workflow details, tool usage, and workspace configurations, ensuring all operational aspects are accurately documented.
       - **Trigger:** Activated upon the successful completion of the Expert Agent's task, maintaining a streamlined process flow.
       - **Output:** Generates structured data logs that are crucial for the Analysis Model Agent’s operations.
        - API: ag:13e82541:20241025:Memory-model-agent-prompt:ccc270fb

    3. **Analysis Model Agent**:
       - **Role:** Analyzes the collected data to create logical flowcharts and detailed operational guides, translating complex data into actionable insights.
       - **Trigger:** Commences operations once the Memory Model Agent completes its data logging, ensuring a continuous workflow.
       - **Output:** Provides comprehensive guides and analysis reports that are instrumental for training purposes and operational improvements.
        - API: ag:13e82541:20241025:analysis-model-agent-prompt:c1d46050

    #### Workflow Management:
    - **Data Synchronization:** Implements mechanisms to ensure real-time data sharing and synchronization across all agents using a centralized database or shared environment variables. This facilitates immediate data availability and consistency.
    - **Error Handling:** Incorporates robust error detection and recovery mechanisms to handle failures in agent tasks efficiently. This includes options for retries or alternative measures based on predefined conditions, minimizing downtime and enhancing system resilience.
    - **Monitoring and Logging:** Utilizes advanced monitoring tools to track the status and performance of all agents. Detailed logs are maintained for audit and optimization purposes, ensuring transparency and enabling continuous improvement.

    #### Usage:
    This workflow is tailored for organizations aiming to automate and streamline complex operational processes. It enhances data accuracy and significantly improves decision-making capabilities through detailed analysis and reporting.

    #### Instructions:
    - **Initiation:** To initiate the Master Workflow, execute the command: `mistral execution-create Master_Workflow`.
    - **Monitoring:** Continuously monitor the workflow execution through the Mistral dashboard or CLI to ensure all tasks are progressing as planned and address any anomalies promptly.
    - **Review:** Regularly consult the log files to identify and promptly address any potential issues, ensuring optimal workflow performance.

    #### Note:
    Before launching the workflow, ensure that all agents are properly configured and that necessary permissions and API keys are set up to avoid any disruptions during operations.

    This comprehensive description of the Master Workflow outlines a structured and efficient approach to managing complex operational tasks, ensuring high performance, and fostering an environment of continuous improvement within the organization.
    """


    #planning_result = run_workflow_agent(query)
    #print(f"Planning result: {query}")

#class AgentWorkflow:
#    def __init__(self):
#        pass

    #def run_expert_agent(self, query_expert):
    #    """
    #    Sends a user query to a Python agent and returns the response.
#
    #    Args:
    #        query (str): The user query to be sent to the Python agent.
#
    #    Returns:
    #        str: The response content from the Python agent.
    #    """
    #    print("### Run Expert agent")
    #    print(f"User query: {query_expert}")
    #    try:
    #        response = client.agents.complete(
    #            agent_id= agents['expert'],
    #            messages = [
    #                {
    #                    "role": "user",
    #                    "content":  query_expert
    #                },
    #            ]
    #        )
    #        result = response.choices[0].message.content
    #        return result
#
    #    except Exception as e:
    #        print(f"Request failed: {e}. Please check your request.")
    #        return None
    async def run_memory_agent(self):
        """运行内存代理并返回结果"""
        logging.info("### Run Memory agent")
        expert_result = central_database.get('expert_data', '')
        """运行内存代理并返回结果"""
        print("### Run Memory agent")
        # 从中央数据库获取专家数据
        if expert_result:
            result = await self.perform_task(agents['memory'], expert_result)
            logging.info(f"Memory agent result: {result}")
            # 将结果存入中央数据库
            central_database['memory_data'] = result
            return result
        else:
            logging.error("Expert data not found in central database. Please check the workflow or central database.")
            return None
        #result = await perform_task(agents['memory'], expert_result)
        #logging.info(f"Memory agent result: {result}")
        # 将结果存入中央数据库
        #central_database['memory_data'] = result
        #return result
        #except Exception as e:
            #logging.error(f"Memory agent request failed: {e}. Please check your request.")
            #return None

    async def run_analysis_agent(self):
        """运行分析代理并返回结果"""
        logging.info("### Run Analysis agent")
        memory_result = central_database.get('memory_data', '')
        try:
            """运行分析代理并返回结果"""
            print("### Run Analysis agent")
            # 从中央数据库获取内存数据
            if memory_result:
                result = await self.perform_task(agents['analysis'], memory_result)
                logging.info(f"Analysis agent result: {result}")
                # 将结果存入中央数据库
                central_database['analysis_data'] = result
                return result
            else:
                logging.error("Memory data not found in central database. Please check the workflow or central database.")
                return None
        except Exception as e:
            logging.error(f"Analysis agent request failed: {e}. Please check your request.")
            return None

    async def workflow(self, initial_query):
        """执行工作流"""
        logging.info("### Starting workflow")
        expert_result = await self.run_expert_agent(initial_query)
        if expert_result:
            memory_result = await self.run_memory_agent()#expert_result)
            if memory_result:
                analysis_result = await self.run_analysis_agent()#memory_result)
                logging.info(f"Final Analysis Result: {analysis_result}")
                print(f"Final Analysis Result: {analysis_result}")

# 示例用法，定义主异步函数
async def main():
    initial_query = "how to drill a hole into a wooden block"
    agent_workflow = AgentWorkflow()
    try:
        await agent_workflow.workflow(initial_query)
    except Exception as e:
        logging.error(f"Workflow execution failed: {e}. Please check the workflow.")
        print(f"Workflow execution failed: {e}. Please check the workflow.")
    finally:    
        await agent_workflow.close()

# 运行主函数
if __name__ == "__main__":
    asyncio.run(main())