from config import API_KEY
import asyncio
from localStoragePy import localStoragePy
from mistralai import Mistral
from aiohttp import ClientSession
import re
import logging
import pandas as pd
import base64
from io import BytesIO
from PIL import Image
import json
import csv
import logging

csv_file_path = '/mnt/Data/bosong/agent/log.csv'

# 读取图像并将其编码为 Base64
def encode_image(img):
    with open(img, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

logging.basicConfig(filename='workflow.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 初始化 Mistral 客户端
client = Mistral(api_key=API_KEY)
model = "pixtral-12b-2409"

# 代理 ID 字典
agents = {
    'memory': "ag:13e82541:20241025:untitlerecord-model-agent-promptd-agent:ccc270fb",
    'expert': "ag:13e82541:20241025:expert-agent:338569a8",
    'analysis': "ag:13e82541:20241025:analysis-model-agent-prompt:c1d46050",
    'workflow': "ag:13e82541:20241025:master-workflow:7bcaf579"
}

# 中央数据库，用于存储各个代理的结果和状态信息
central_database = {
    'tool_inventory': [],
    'workspace_configurations': [],
    'expert_data': "",  # 用于存储专家代理的结果
    'memory_data': pd.DataFrame(columns=["Timestamp", "Object", "Action"]),  # 用于存储从 CSV 文件读取的数据
}

class AgentWorkflow:
    def __init__(self, csv_file_path):
        self.client_session = ClientSession()
        self.csv_file_path = csv_file_path
        
    async def read_csv_data(self):
        """Read data from a CSV file and update central database."""
        try:
            with open(self.csv_file_path, mode='r', newline='') as file:
                reader = csv.DictReader(file)
                central_database['memory_data'] = pd.DataFrame(reader)
        except FileNotFoundError:
            central_database['memory_data'] = pd.DataFrame(columns=["Timestamp", "Object", "Action"])
            print("CSV file not found. Created a new dataframe.")
        except Exception as e:
            print(f"Error reading CSV file: {e}")
            # Optionally, create an empty DataFrame on any error
            central_database['memory_data'] = pd.DataFrame(columns=["Timestamp", "Object", "Action"])

    async def write_csv_data(self):
        """Write the central database to a CSV file."""
        try:
            central_database['memory_data'].to_csv(self.csv_file_path, index=False)
            print("Data written to CSV successfully.")
        except Exception as e:
            print(f"Failed to write to CSV: {e}")
        
    async def close(self):
        """关闭资源，确保客户端会话被正确关闭"""
        await self.client_session.close()

    async def perform_task(self, agent_id, question, base64_image):
        """异步执行任务并获取响应"""
        url = f"https://api.mistral.ai/v1/agents/completions"
        headers = {'Authorization': f'Bearer {API_KEY}',
                    'Content-Type': 'application/json'}
        params = {
            "agent_id": agent_id,
            "messages": [
                {
                    "role": "user", 
                    "content":[
                        {
                            "type": "text",
                            "text": question
                        },
                        {
                            "type": "image_url",
                            "image_url": f"data:image/jpeg;base64,{base64_image}"
                        } 
                    ] 
                },
            ]
        }
        
        async with self.client_session.post(url, json=params, headers=headers) as response:
            data = await response.json()  # Directly parse the JSON response
            logging.info(f"Response from {agent_id}: data: {data}")
            if 'choices' in data and data['choices']:
                return data['choices'][0]['message']['content']
            else:
                logging.error(f"Unexpected response format: {data}")
                logging.error(f"HTTP error {response.status}: {await response.text()}")
                raise ValueError("Invalid response format from API.")


    async def run_expert_agent(self, query_expert, base64_image):
        """运行专家代理并返回结果"""
        print("### Run Expert agent")
        logging.info("### Run Expert agent")
        try:
            result = await self.perform_task(agents['expert'], query_expert, base64_image)
            central_database['expert_data'] = result  # 将结果存储在中央数据库中
            logging.info(f"Expert agent returned result: {result}")
            return result
        except Exception as e:
            logging.error(f"Failed to run expert agent: {e}")
            print(f"Error: {e}")
            # 根据错误类型和重要性，可以选择重新尝试或返回特定错误信息
            return None
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
    
    async def run_memory_agent(self, base64_image):
        logging.info("### Run Memory agent")
        print("### Run Memory agent")
        expert_result = central_database.get('expert_data', '')

        await self.read_csv_data()  # Read existing data from CSV
        central_database['memory_data'] = pd.read_csv(self.csv_file_path)
        logging.info("CSV data successfully read and memory data updated.")
        # 输出当前内存数据内容
        #logging.info(f"Current Memory Data:\n{central_database['memory_data']}")
        
        if expert_result:
            memory_result_json = central_database['memory_data'].to_json(orient='records')
            result = await self.perform_task(agents['memory'], expert_result+memory_result_json, base64_image)
            logging.info(f"Memory agent result: {result}")

            if result:
                try:
                    # 假设 result 是一个字典，可以直接转换为 DataFrame
                    new_record = pd.DataFrame([result])  # 直接将字典列表转换为 DataFrame
                    central_database['memory_data'] = pd.concat([central_database['memory_data'], new_record], ignore_index=True)
                    logging.info(f"Memory agent returned result: {result}")
                    await self.write_csv_data()  # 成功处理后写入 CSV
                    return result
                except Exception as e:  # 捕获所有可能的错误
                    logging.error(f"Failed to process memory agent result: {e}")
                    return None
            else:
                logging.error("No result returned from memory agent.")
                return None
        else:
            logging.error("Expert data not found in central database. Please check the workflow or central database.")
            return None

        """从 CSV 文件加载数据并更新内存代理"""
#        try:
#            for index, row in df.iterrows():
#                timestamp = row['Timestamp']
#                object_name = row['Object']
#                action = row['Action']
#                # 更新内存数据框
#                central_database['memory_data'] = central_database['memory_data'].append(
#                    {"Timestamp": timestamp, "Object": object_name, "Action": action}, ignore_index=True)
#            logging.info("Data loaded successfully from CSV.")
#        except Exception as e:
#            logging.error(f"Failed to load data from CSV: {e}")

        """更新内存数据中的特定行"""
        if not central_database['memory_data'].empty:
            for index, row in central_database['memory_data'].iterrows():
                if row["Timestamp"] == timestamp:
                    if object_name is not None:
                        central_database['memory_data'].at[index, 'Object'] = object_name
                    if action is not None:
                        central_database['memory_data'].at[index, 'Action'] = action
                    logging.info(f"Updated memory data for timestamp {timestamp}.")
                    return True
        logging.warning(f"No entry found for timestamp {timestamp}.")
        return False

        """查询特定时间戳的数据"""
        if not central_database['memory_data'].empty:
            result = central_database['memory_data'][central_database['memory_data']['Timestamp'] == timestamp]
            return result if not result.empty else None
        return None


    async def run_analysis_agent(self, base64_image):
        """运行分析代理并返回结果"""
        logging.info("### Run Analysis agent")
        memory_result = central_database.get('memory_data', '')
        try:
            """运行分析代理并返回结果"""
            print("### Run Analysis agent")
            # 从中央数据库获取内存数据
            if not memory_result.empty:
                result = await self.perform_task(agents['analysis'], memory_result, base64_image)
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

    async def workflow(self, initial_query, base64_image):
            """Execute the workflow with CSV operations."""
            logging.info("### Starting workflow")
            await self.read_csv_data()  # Read existing data from CSV
            expert_result = await self.run_expert_agent(initial_query, base64_image)
            if expert_result:
                memory_result = await self.run_memory_agent(base64_image)
                if memory_result:
                    analysis_result = await self.run_analysis_agent(base64_image)
                    logging.info(f"Final Analysis Result: {analysis_result}")
                    print(f"Final Analysis Result: {analysis_result}")
                    #await self.write_csv_data()  # Write updated data to CSV

async def main():
    #img = "/mnt/logicNAS/Exchange/Aria/User_16/test2.jpg"
    img = "/mnt/logicNAS/Exchange/Aria/User_16/gaze/04550.jpg"
    base64_image = encode_image(img)
    initial_query =(f"Analyse the image and tell me what is the object shown in highlight: the circle with star is the eye gaze point, which I am looking at the point, the highlighted area is the segmentation of the whole area of the object I am working with. The information of the picture is from the video frame of timestamp, the file name is the timestamp from path {img}, show me a table with one column timestamp, second column is object(the highlighted color area of segmentation with label) please detect and analyse the item or object, third column is the action prediction. Send these messages into the memory agent and give me the result in table and save it into central memory station." )

    agent_workflow = AgentWorkflow(csv_file_path=csv_file_path)

    try:
        await agent_workflow.workflow(initial_query, base64_image)
    except Exception as e:
        logging.error(f"Workflow execution failed: {e}. Please check the workflow.")
        print(f"Workflow execution failed: {e}. Please check the workflow.")
    finally:    
        await agent_workflow.close()

if __name__ == "__main__":
    csv_file_path = '/mnt/Data/bosong/agent/log.csv'
    asyncio.run(main())