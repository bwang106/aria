import asyncio
import sqlite3
import base64
import logging
from aiohttp import ClientSession

from config import API_KEY
from mistralai import Mistral

logging.basicConfig(filename='workflow2.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 代理 ID 字典
agents = {
'memory': "ag:13e82541:20241025:untitlerecord-model-agent-promptd-agent:ccc270fb",
'expert': "ag:13e82541:20241025:expert-agent:338569a8",
'analysis': "ag:13e82541:20241025:analysis-model-agent-prompt:c1d46050",
'workflow': "ag:13e82541:20241025:master-workflow:7bcaf579"
}
# Database setup
def db_connection():
    con = sqlite3.connect("tutorial.db")
    cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS item(name TEXT, location TEXT, status TEXT)")
    return con, cur

# Read and encode image
def encode_image(img_path):
    with open(img_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

class AgentWorkflow:
    def __init__(self, client):
        self.client = client

    async def perform_task(self, agent_id, question, base64_image):
        url = "https://api.mistral.ai/v1/agents/completions"
        headers = {'Authorization': f'Bearer {API_KEY}', 'Content-Type': 'application/json'}
        params = {
            "agent_id": agent_id,
            "messages": [{"role": "user", "content": [{"type": "text", "text": question}, {"type": "image_url", "image_url": f"data:image/jpeg;base64,{base64_image}"}]}]
        }
        async with ClientSession() as session:
            async with session.post(url, json=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    logging.debug(f"API Response: {data}")
                    return data['choices'][0]['message']['content'] if 'choices' in data and 'message' in data['choices'][0] else None
                else:
                    logging.error(f"HTTP error {response.status}: {await response.text()}")
                    return None

    async def run_expert_agent(self, query, image):
        logging.info("Running Expert Agent")
        result = await self.perform_task(agents['expert'], query, image)
        if result and isinstance(result, dict) and all(k in result for k in ['name', 'location', 'status']):
            con, cur = db_connection()
            cur.executemany("INSERT INTO item(name, location, status) VALUES (?, ?, ?)", [(result['name'], result['location'], result['status'])])
            con.commit()
            self.print_database_output(con)
            con.close()
        else:
            logging.error("Invalid or missing data from expert agent.")
        return result
    
    def print_database_output(self, con):
        cur = con.cursor()
        cur.execute("SELECT name, location, status FROM item")
        rows = cur.fetchall()
        if rows:
            print("Database Contents:")
            for row in rows:
                print(f"Name: {row[0]}, Location: {row[1]}, Status: {row[2]}")
        else:
            print("No data found in the database.")
            
    async def workflow(self, query, image):
        logging.info("Starting workflow")
        expert_result = await self.run_expert_agent(query, image)
        if expert_result:
            logging.info(f"Workflow completed with result: {expert_result}")
        else:
            logging.error("Workflow failed due to expert agent issues.")

async def main():
    img_path = "/mnt/logicNAS/Exchange/Aria/User_16/gaze/04550.jpg"
    base64_image = encode_image(img_path)
    initial_query = "Analyze the image and provide details."

    client = Mistral(api_key=API_KEY)
    agent_workflow = AgentWorkflow(client)

    try:
        await agent_workflow.workflow(initial_query, base64_image)
    except Exception as e:
        logging.error(f"Workflow execution failed: {e}")
        print("Workflow execution failed. Check logs for details.")
    finally:
        logging.info("Workflow completed.")

if __name__ == "__main__":
    asyncio.run(main())