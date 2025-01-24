import os
import time
import logging
import google.generativeai as genai
from config import GEMINI_API_KEY
import pandas as pd
import re
import csv
import sys
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("gemini_agent.log"),  # Log to a file
        logging.StreamHandler()  # Also log to console
    ]
)

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# Define the base path for results
RESULT_BASE_PATH = "/mnt/Data/bosong/agent/result_gemini-2.0-flash-exp"
#RESULT_BASE_PATH = "/mnt/Data/bosong/agent/result_gemini-2.0-flash-thinking-exp-1219"

# Define the path to your Excel file
DATABANK_FILE = os.path.join(RESULT_BASE_PATH, "tool_databank.csv")

# Define the path to your CSV file
CSV_FILE = os.path.join(RESULT_BASE_PATH, "gemini_output.csv")

def upload_to_gemini(path, mime_type=None):
    """Uploads the given file to Gemini."""
    try:
        file = genai.upload_file(path, mime_type=mime_type)
        logging.info(f"Uploaded file '{file.display_name}' as: {file.uri}")
        return file
    except Exception as e:
        logging.error(f"Failed to upload file {path}: {str(e)}")
        return None

def wait_for_files_active(files):
    """Waits for the given files to be active."""
    logging.info("Waiting for file processing...")
    for name in (file.name for file in files):
        file = genai.get_file(name)
        while file.state.name == "PROCESSING":
            # 使用 sys.stdout.write() 来输出点而不换行
            sys.stdout.write(".")
            sys.stdout.flush()  # 立即刷新输出
            time.sleep(10)
            file = genai.get_file(name)
        if file.state.name != "ACTIVE":
            logging.error(f"File {file.name} failed to process")
            raise Exception(f"File {file.name} failed to process")
    logging.info("...all files ready")
    logging.info(f"File {file.name}")  # 为了更好的可读性添加换行

# Create the model
generation_config = {
    "temperature": 0.2,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
    model_name="gemini-2.0-flash-exp",
    #model_name="gemini-2.0-flash-thinking-exp-1219",
    generation_config=generation_config,
    system_instruction="""You are an AI assistant, helping the worker. Analyze the video and identify all instances where the user is holding a tool (e.g., screwdrivers, pliers, wrenches) or an object (e.g., boxes, packaging materials). For each instance, provide:
- Precise timestamps for when the tool or object is held.
- Detailed descriptions of each action or movement involving the tool or object, including how the user is using it. For example, "using a screwdriver to fasten a bolt."
- Detailed descriptions of the shape (e.g., round, square, rectangular, irregular) and size (e.g., length, width, height, diameter) of each tool or object.

Output the results in a structured format that can be easily parsed:
1. Provide a summary of the identified tools and objects in a table format with the following columns: timestamp, object, estimated action.
2. Include a JSON object with detailed descriptions of each tool, which can be used directly in the update function. The JSON should include the fields with table and description of objects and actions needs to be accurate and complete,**Output the results in a structured JSON format**:
{
    "video_name": "",
    "tools": [
        {
            
            "object_name": "",
            "object_type": "",
            "object_color": "",
            "object_size": "",
            "action": "",
            "timestamp": ""
        },
        ...
    ]
}
Ensure that the output is valid JSON and does not contain any additional textual explanations or interpretations, video_name should be the input video name

Ensure that repeat frame is minimized, but the description of objects and actions needs to be accurate and complete.:
- If the action does not change for more than 6 seconds, only include the timestamps for the start, middle, and end of that action.
- Provide a summary after the table that explains the behavior of the user with respect to the tools and objects.

Additionally, extract the table data into a CSV file for subsequent reading and writing. Identify all tools and objects held by the user in the video, and ensure the analysis is thorough and accurate.
"""
)

def extract_tool_info(response_text):
    """Extracts tool information from the response text."""
    logging.info("Extracting tool information from Gemini's response...")
    # Define a regular expression to match the table format
    table_regex = re.compile(r"\| Timestamp \| Object \| Estimated Action \|\n\|---?\|---?\|---?\|([\s\S]*?)(?=\n\n|$)", re.MULTILINE)
    match = table_regex.search(response_text)
    if not match:
        logging.warning("No tool information found in Gemini's response.")
        return None

    table_content = match.group(1).strip()
    rows = table_content.split("\n")
    data = []
    for row in rows:
        parts = [part.strip() for part in row.split("|")[1:-1]]
        if len(parts) == 3:
            data.append(parts)
    
    df = pd.DataFrame(data, columns=['timestamp', 'object', 'action'])
    logging.info("Tool information extracted successfully.")
    return df

def update_databank(new_tool_info):
    """Updates the databank with new tool information."""
    try:
        # 先检查文件是否存在并读取数据
        if os.path.exists(DATABANK_FILE) and os.path.getsize(DATABANK_FILE) > 0:
            df = pd.read_csv(DATABANK_FILE)
        else:
            # 如果文件不存在或为空，则创建一个新的 DataFrame
            df = pd.DataFrame(columns=['timestamp', 'object', 'object_type', 'object_color', 'object_size', 'action', 'status', 'location'])
            logging.warning("Databank file not found or is empty. Creating a new dataframe.")
        
    except Exception as e:
        logging.error(f"Error reading databank file: {str(e)}")
        return
    if new_tool_info:
        # 处理 JSON 输出
        for tool_info in new_tool_info:
            object_name = tool_info['object_name']
            action = tool_info['action']
            timestamp = tool_info['timestamp']
            object_type = tool_info.get('object_type', 'Unknown')
            object_color = tool_info.get('object_color', 'Unknown')
            object_size = tool_info.get('object_size', 'Unknown')

            # 检查工具是否已存在
            existing_tool = df[(df['object'] == object_name)]
            if not existing_tool.empty:
                # 更新现有工具信息
                df.loc[existing_tool.index, 'timestamp'] = timestamp
                df.loc[existing_tool.index, 'action'] = action
                df.loc[existing_tool.index, 'status'] = "Normal"
                logging.info(f"Updated information for tool: {object_name}")
            else:
                # 添加新工具信息
                new_row = {
                    'timestamp': timestamp,
                    'object': object_name,
                    'object_type': object_type,
                    'object_color': object_color,
                    'object_size': object_size,
                    'action': action,
                    'status': "Normal",
                    'location': "Unknown"
                }
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                logging.info(f"Added new tool: {object_name}")

    df.to_csv(DATABANK_FILE, index=False)
    logging.info("Databank updated successfully.")

def query_databank(tool_name):
    """Queries the databank for information about a specific tool."""
    logging.info(f"Querying databank for tool: {tool_name}...")
    try:
        df = pd.read_csv(DATABANK_FILE)
        if df.empty:
            logging.warning("Databank is empty. No tools to query")
            return None
    except FileNotFoundError:
        logging.error("Databank file not found.")
        return None

    # 查找工具信息
    tool_info = df[df['object'] == tool_name]
    if tool_info.empty:
        logging.warning(f"Tool '{tool_name}' not found in the databank.")
        return None
    else:
        logging.info(f"Information for tool '{tool_name}':")
        logging.info(tool_info)
        return tool_info

def save_gemini_output(response_text):
    """Saves Gemini's output to a CSV file."""
    logging.info("Saving Gemini's output...")
    # Create the directory if it doesn't exist
    os.makedirs(os.path.dirname(CSV_FILE), exist_ok=True)
    
    with open(CSV_FILE, 'a', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        # Write header if the file is new
        if csvfile.tell() == 0:
            writer.writerow(['timestamp', 'response_text'])
        # Write the response text
        writer.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), response_text])
    logging.info(f"Gemini output saved to: {CSV_FILE}")

def find_and_sort_mp4_files(folder_path):
    """Finds and sorts MP4 files in a given folder by filename."""
    mp4_files = [f for f in os.listdir(folder_path) if f.endswith(".mp4")]
    mp4_files.sort(key=lambda f: int(re.search(r'clip_(\d+)', f).group(1)) if re.search(r'clip_(\d+)', f) else float('inf'))
    return [os.path.join(folder_path, f) for f in mp4_files]

#class GeminiAgent:
#    def __init__(self, model):
#        self.model = model
#        self.total_input_tokens = 0
#        self.total_output_tokens = 0
#
#    def generate_content(self, parts):
#        """Generates content with Gemini, tracks tokens, and returns response text."""
#        try:
#            response = self.model.generate_content(parts)
#
#            # Log the token usage
#            if response.prompt_feedback and response.prompt_feedback.token_count:
#                self.total_input_tokens += response.prompt_feedback.token_count
#                logging.info(f"Used {response.prompt_feedback.token_count} input tokens")
#                logging.info(f"Current total input tokens: {self.total_input_tokens}")
#
#            # Log the output token usage
#            if response.text:
#                self.total_output_tokens += len(response.text) // 4  #Rough estimate: 4 characters for 1 token
#                logging.info(f"Used {len(response.text) //4 } output tokens")
#                logging.info(f"Current total output tokens: {self.total_output_tokens}")
#
#
#            return response.text
#        except Exception as e:
#            logging.error(f"Error from Gemini API: {str(e)}")
#            return None

# Main function
def main():
    logging.info("Starting main function...")
    video_folder = "/mnt/logicNAS/Exchange/Aria/User_16/video_seg_90/"  

    # Get and sort the MP4 files
    video_files = find_and_sort_mp4_files(video_folder)
    
    all_tool_info=[]
#    gemini_agent = GeminiAgent(model)

    for video_path in video_files:
        logging.info(f"Processing video file: {video_path}")
        # Upload the video file
        files = [upload_to_gemini(video_path, mime_type="video/mp4")]

        # Wait for the file to be ready
        wait_for_files_active(files)
        # Start a chat session
        logging.info("Starting chat session...")
        chat_session = model.start_chat(
            history=[
                {
                    "role": "user",
                    "parts": [
                        files[0],
                    ],
                },
                {
                    "role": "user",
                    "parts": [
                        """You are an AI assistant, helping the worker. Analyze the video and identify all instances where the user is holding a tool (e.g., screwdrivers, pliers, wrenches) or an object (e.g., boxes, packaging materials). 
Ensure that the output is valid JSON and does not contain any additional textual explanations or interpretations, video_name should be the input video name

Ensure that repeat frame is minimized, but the description of objects and actions needs to be accurate and complete.:
- If the action does not change for more than 6 seconds, only include the timestamps for the start, middle, and end of that action.
- Provide a summary after the table that explains the behavior of the user with respect to the tools and objects.

Additionally, extract the table data into a JSON/CSV file for subsequent reading and writing. Identify all tools and objects held by the user in the video, and ensure the analysis is thorough and accurate.
                    """],
                },
            ]
        )

        # Send the message to Gemini
        logging.info("Sending message to Gemini...")
        response_text = chat_session.send_message("Extract tool and action information from the videos. Analyze the video and identify all instances, extract the table data into a JSON/CSV file for subsequent reading and writing.")

        #check if response is empty before parsing
        if not response_text:
            logging.warning("Received empty response from Gemini.")
            continue #skip to next video

        # Save Gemini's output
        save_gemini_output(response_text)
        
        #tool_info_df = extract_tool_info(response.text)
#        try:
#            # Remove any leadingjson and trailing
#            if response.text.startswith("json"): response_text = response.text[7:-3].strip() # 7 for 'json' and 3 for '' 
#            else: response_text = response.text.strip()
#            # Now attempt to load the JSON
#            tool_info_json = json.loads(response_text)
#            all_tool_info.extend(tool_info_json['tools'])  # Add the extracted tool info to the list
#            logging.info(f"Extracted tool info for video '{tool_info_json['video_name']}': {tool_info_json['tools']}")  # Log extracted info
#
#        except json.JSONDecodeError as e:
#            logging.error(f"Failed to decode JSON from response: {str(e)}")
#            logging.error(f"Raw response content: {response.text}")  # Log the raw response
#            continue  # Skip to the next video
#        try:
#            # Attempt to find a JSON object within the response text
#            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
#            if json_match:
#                json_str = json_match.group(0)
#                try:
#                    tool_info_json = json.loads(json_str)
#                    if 'tools' in tool_info_json:
#                        all_tool_info.extend(tool_info_json['tools'])
#                        logging.info(f"Extracted tool info for video '{tool_info_json.get('video_name', 'Unknown')}': {tool_info_json['tools']}")
#                    else:
#                        logging.warning("No 'tools' key found in JSON response.")
#                except json.JSONDecodeError as e:
#                    logging.error(f"Failed to decode JSON from response: {str(e)}")
#                    logging.error(f"Raw response content: {json_str}")  # Log the raw response
#                    continue  # Skip to the next video
#            else:
#                logging.warning("No JSON object found in Gemini's response.")
#                continue
#        except Exception as e:
#            logging.error(f"Error processing response: {str(e)}")
#            continue
#       #假设 response.text 包含 JSON 格式的工具信息
#change from 2001 1912
        try:
            # 检查 response_text 是否为有效字符串
            if not isinstance(response_text, str):
                raise ValueError(f"Expected string input, but got {type(response_text)}.")
    
            # 使用正则表达式查找 JSON 对象
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
    
            if json_match:
                json_str = json_match.group(0)
                tool_info_json = json.loads(json_str)
    
                if 'tools' in tool_info_json:
                    video_name = tool_info_json.get("video_name", "Unknown Video")
                    tools = tool_info_json['tools']
    
                    # 记录视频名称以供参考
                    logging.info(f"Processing video: {video_name}")
    
                    # 从 JSON 文件加载当前工具信息
                    existing_tools = load_tool_info_from_json(json_file)
                    updated_tools_info = []
    
                    # 处理每个工具
                    for tool in tools:
                        # 检查更新并记录工具信息
                        existing_tool = next((t for t in existing_tools if t.get("object_name") == tool.get("object_name")), None)
                        if existing_tool:
                            # 更新现有工具信息（这里可以根据需求进行更新）
                            updated_tool_info = {
                                "video_name": video_name,
                                "object_name": tool.get("object_name", ""),
                                "object_type": tool.get("object_type", existing_tool.get("object_type", "")),
                                "object_color": tool.get("object_color", existing_tool.get("object_color", "")),
                                "object_size": tool.get("object_size", existing_tool.get("object_size", "")),
                                "action": tool.get("action", ""),
                                "timestamp": tool.get("timestamp", "")
                            }
                            updated_tools_info.append(updated_tool_info)
                        else:
                            # 新工具信息
                            updated_tools_info.append({
                                "video_name": video_name,
                                "object_name": tool.get("object_name", ""),
                                "object_type": tool.get("object_type", ""),
                                "object_color": tool.get("object_color", ""),
                                "object_size": tool.get("object_size", ""),
                                "action": tool.get("action", ""),
                                "timestamp": tool.get("timestamp", "")
                            })
    
                    # 在此处理更新的工具信息（例如保存到文件或数据库）
                    save_updated_tools_info(updated_tools_info)  # 伪代码，您需要实现此函数
    
                else:
                    logging.warning("No 'tools' key found in JSON response.")
            else:
                logging.warning("No JSON object found in Gemini's response.")
    
        except json.JSONDecodeError as e:
            logging.error(f"Failed to decode JSON from response: {str(e)}")
        except Exception as e:
            logging.error(f"An unexpected error occurred while processing video {video}: {str(e)}")
            continue  # Skip to the next video
#       try:
#           #tool_info_json = json.loads(response.text)
#           #all_tool_info.extend(tool_info_json)
#           response_data = json.loads(response_text)
#           video_name = response_data.get("video_name", "Unknown Video")
#           tools = response_data.get("tools", [])#
#           # Log the video name for reference
#           logging.info(f"Processing video: {video_name}")#
#           # Process each tool in the tools list
#           for tool in tools:
#               all_tool_info.append({
#                   "video_name": video_name,
#                   "object_name": tool.get("object_name", ""),
#                   "object_type": tool.get("object_type", ""),
#                   "object_color": tool.get("object_color", ""),
#                   "object_size": tool.get("object_size", ""),
#                   "action": tool.get("action", ""),
#                   "timestamp": tool.get("timestamp", "")
#               })
#       except json.JSONDecodeError as e:
#           logging.error(f"Failed to decode JSON from response{str(e)}:")
#           #logging.error(f"Response text{response.text}:")
#           continue #skip to the next video
#   
#       # 更新数据银行
        #update_databank(tool_info_json)
#
        ## Extract tool information from the response
        #tool_info_df = extract_tool_info(response.text)
        #if tool_info_df is not None:
        #    # Update the databank
        #    update_databank(tool_info_df)
        #else:
        #    logging.warning("No tool information extracted from the response.")
        #    update_databank(pd.DataFrame(columns=['timestamp', 'object', 'action']))  # Update with empty df

    # Example: Query the databank for a specific tool
    #tool_to_query = "#3 red screwdriver"
    #query_result = query_databank(tool_to_query)
    
    #summerize dataframe
    if all_tool_info:
        summary_df= pd.DataFrame(all_tool_info)
        # 更新数据银行
        update_databank(all_tool_info)

        # 保存汇总到 CSV 文件
        summary_df.to_csv(DATABANK_FILE, index=False)
        logging.info(f"Summary of tool information saved to: {DATABANK_FILE}")
    else:
        logging.warning("No tool information collected from any video.")

    # Estimate the total cost
#    estimated_cost = (gemini_agent.total_input_tokens * 0.0000025 + gemini_agent.total_output_tokens * 0.000008)  # Replace with actual prices
#    logging.info(f"Estimated total input tokens: {gemini_agent.total_input_tokens}")
#    logging.info(f"Estimated total output tokens: {gemini_agent.total_output_tokens}")
#    logging.info(f"Estimated total cost of processing all videos: ${estimated_cost:.6f}")
    logging.info("Main function completed.")


if __name__ == "__main__":
    main()