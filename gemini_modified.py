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
        logging.FileHandler("gemini_agent.log"),
        logging.StreamHandler()
    ]
)

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# Define the base path for results
RESULT_BASE_PATH = "/mnt/Data/bosong/agent/result_gemini-2.0-flash-exp"
#RESULT_BASE_PATH = "/mnt/Data/bosong/agent/result_gemini-2.0-flash-thinking-exp-1219"
DATABANK_FILE = os.path.join(RESULT_BASE_PATH, "tool_databank.csv")
CSV_FILE = os.path.join(RESULT_BASE_PATH, "gemini_output.csv")

# Create the model
generation_config = {
    "temperature": 0.2,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 12000,
    "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
    model_name="gemini-2.0-flash-exp",
    #model_name="gemini-2.0-flash-thinking-exp-1219",
    generation_config=generation_config,
    #system_instruction="You are an AI assistant, helping the worker to analyze videos with following all roles. You are a coding expert which has ability with analyse video contents and with annotation you can better understand the user action with interaction with the tools with time stamp in logic, after each movement or actions finished you have ability with remember what was the user doing, which tools does the task need, where is the tools and what is the status of the tools. Use memory bank to remenber  all the necessary information. If in the future another user is asking to do the same task, the agent will able to access the memory bank to have the instrction with the whole task include the tools and actions and other informations."
)

def wait_for_files_active(files):
    """Waits for the given files to be active."""
    logging.info("Waiting for file processing...")
    for name in (file.name for file in files):
        file = genai.get_file(name)
        while file.state.name == "PROCESSING":
            sys.stdout.write(".")
            sys.stdout.flush()
            time.sleep(10)
            file = genai.get_file(name)
        if file.state.name != "ACTIVE":
            logging.error(f"File {file.name} failed to process")
            raise Exception(f"File {file.name} failed to process")
    logging.info("...all files ready")

def save_gemini_output(response_text):
    """Saves Gemini's output to a CSV file."""
    logging.info("Saving Gemini's output...")
    os.makedirs(os.path.dirname(CSV_FILE), exist_ok=True)
    
    with open(CSV_FILE, 'a', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        if csvfile.tell() == 0:
            writer.writerow(['timestamp', 'response_text'])
        writer.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), response_text])
    logging.info(f"Gemini output saved to: {CSV_FILE}")

def find_and_sort_mp4_files(folder_path):
    """Finds and sorts MP4 files by filename."""
    mp4_files = [f for f in os.listdir(folder_path) if f.endswith(".mp4")]
    mp4_files.sort(key=lambda f: int(re.search(r'clip_(\d+)', f).group(1)) if re.search(r'clip_(\d+)', f) else float('inf'))
    return [os.path.join(folder_path, f) for f in mp4_files]

#def is_valid_response(response_text):
#    """Checks if the response text is valid"""
#    return isinstance(response_text, str) and len(response_text) > 0

def handle_exception(e, context):
    """Logs exception information and context"""
    logging.error(f"Error occurred in {context}: {str(e)}")

def upload_to_gemini(path, mime_type=None):
    """Uploads the given file to Gemini."""
    try:
        file = genai.upload_file(path, mime_type=mime_type)
        logging.info(f"Uploaded file '{file.display_name}' as: {file.uri}")
        return file
    except Exception as e:
        logging.error(f"Failed to upload file {path}: {str(e)}")
        return None

def update_databank(new_tool_info):
    """Updates the databank with new tool information."""
    try:
        logging.info("update_databank")
        if os.path.exists(DATABANK_FILE) and os.path.getsize(DATABANK_FILE) > 0:
            df = pd.read_csv(DATABANK_FILE)
        else:
            df = pd.DataFrame(columns=['timestamp', 'object', 'object_type', 'object_color', 'object_size', 'action', 'status', 'location'])
            logging.warning("Databank file not found or is empty. Creating a new dataframe.")
        
    except Exception as e:
        handle_exception(e, "reading databank file")
        return
    
    if new_tool_info:
        for tool_info in new_tool_info:
            object_name = tool_info['object_name']
            action = tool_info['action']
            timestamp = tool_info['timestamp']
            object_type = tool_info.get('object_type', 'Unknown')
            object_color = tool_info.get('object_color', 'Unknown')
            object_size = tool_info.get('object_size', 'Unknown')

            existing_tool = df[df['object'] == object_name]
            if not existing_tool.empty:
                df.loc[existing_tool.index, ['timestamp', 'action', 'status']] = [timestamp, action, "Normal"]
                logging.info(f"Updated information for tool: {object_name}")
            else:
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

def process_video(video_path):
    """Processes a single video"""
    logging.info(f"Processing video file: {video_path}")
    files = [upload_to_gemini(video_path, mime_type="video/mp4")]
    wait_for_files_active(files)
    chat_session = model.start_chat(
        history=[
            {"role": "user", "parts": [files[0],],},
            {
                "role": "user",
                "parts": [
                    """You are an AI assistant, helping the worker. Analyze the video and identify all instances where the user is holding a tool (e.g., screwdrivers, pliers, wrenches) or an object (e.g., boxes, packaging materials). 
                    For each instance, provide detailed information of:
- Precise timestamps for when the tool or object is held.
- Detailed descriptions of each action or movement involving the tool or object, including how the user is using it. For example, "using a screwdriver to fasten a bolt."
- Detailed descriptions of the shape (e.g., round, square, rectangular, irregular) and size (e.g., length, width, height, diameter) of each tool or object.
- Output the table results in a structured format that can be easily parsed:
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
Ensure that the output is valid JSON and does not contain any additional textual explanations or interpretations, video name should be the input video name or follow the sequence of the video.

Ensure that repeat frame is minimized, but the description of objects and actions needs to be accurate and complete and also be detailed.:
- If the action does not change for more than 6 seconds, only include the timestamps for the start, middle, and end of that action.
- Provide a summary after the table that explains the behavior of the user with respect to the tools and objects.

Additionally, extract the table data into a JSON/CSV file for subsequent reading and writing. Identify all tools and objects held by the user in the video, and ensure the analysis is thorough and accurate.
                    """
                ]
            }
        ]
    )

    response = chat_session.send_message("Extract tool and action information from the videos with following all roles that mentioned.")
    #data = json.loads(response)
    #response_text=data['candidates']['content']['parts'][0]['text']
    #if is_valid_response(response_text):
    #    save_gemini_output(response_text)
    #    extract_and_update_tools(response_text)
    #else:
    save_gemini_output(response.text)
    extract_and_update_tools(response.text)
    #    logging.warning("Received empty or invalid response from Gemini.")

def load_tool_info_from_json(json_file):
    """从 JSON 文件加载工具信息并返回列表"""
    if not os.path.exists(json_file):
        logging.error(f"JSON file does not exist: {json_file}")
        return []

    with open(json_file, 'r') as file:
        try:
            data = json.loads(file)
            return data.get('tools', [])
        except json.JSONDecodeError as e:
            logging.error(f"Failed to decode JSON from file {json_file}: {str(e)}")
            return []
        except Exception as e:
            logging.error(f"An error occurred while loading tools from {json_file}: {str(e)}")
            return []

def extract_and_update_tools(response_text):
    """Extracts tool information and updates the databank"""
    try:
        logging.info("extract_and_update_tools")
        # 读取文件内容
        #file_output="/mnt/Data/bosong/agent/result_gemini-2.0-flash-exp/gemini_output.csv"
        #with open(file_output, 'r') as file:
        #    response_text = file.read()  # 读取文件内容为字符串
        #logging.info("opened")
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        #json_match=response_text
        if json_match:
            json_str = json_match.group(0)
            # 修复 JSON 字符串中多余的双引号replase "" to  
            json_str = json_str.replace('""', ' ')
            # 解析 JSON 字符串
            tool_info_json = json.loads(json_str)
            logging.info("matched")
            
            if 'tools' in tool_info_json:
                video_name = tool_info_json.get("video_name", "Unknown Video")
                tools = tool_info_json['tools']

                logging.info(f"Processing video: {video_name}")
                existing_tools = load_tool_info_from_json(DATABANK_FILE)
                if not existing_tools:
                    logging.warning(f"No tools found in {DATABANK_FILE}, attempting to load from secondary CSV file.")
                    existing_tools = load_tool_info_from_json(CSV_FILE)  # 尝试从第二个 CSV 文件加载
                
                logging.info("load_tool_info_from_json databank_file")
                updated_tools_info = []

                for tool in tools:
                    logging.info("test point1")
                    existing_tool = next((t for t in existing_tools if t.get("object_name") == tool.get("object_name")), None)
                    logging.info("test point2")
                    if existing_tool:
                        updated_tool_info = {
                            "video_name": video_name,
                            "object_name": tool.get("object_name", ""),
                            "object_type": tool.get("object_type", tool.get("object_type", existing_tool.get("object_type", ""))),# Example of conditional update
                            "object_color": tool.get("object_color", tool.get("object_color", existing_tool.get("object_color", ""))), # Example of conditional update
                            "object_size": tool.get("object_size", tool.get("object_size", existing_tool.get("object_size", ""))), # Example of conditional update
                            "action": tool.get("action", ""),
                            "timestamp": tool.get("timestamp", "")
                        }
                        updated_tools_info.append(updated_tool_info)
                    else:
                        logging.info(f"New tool detected: {tool.get('object_name')}")
                        updated_tools_info.append({
                            "video_name": video_name,
                            "object_name": tool.get("object_name", ""),
                            "object_type": tool.get("object_type", ""),
                            "object_color": tool.get("object_color", ""),
                            "object_size": tool.get("object_size", ""),
                            "action": tool.get("action", ""),
                            "timestamp": tool.get("timestamp", "")
                        })

                save_updated_tools_info(updated_tools_info)

            else:
                logging.warning("No 'tools' key found in JSON response.")
        else:
            logging.warning("No JSON object found in Gemini's response.")

    except json.JSONDecodeError as e:
        handle_exception(e, "extract_and_update_tools")
    except Exception as e:
        handle_exception(e, "extract_and_update_tools")

def save_updated_tools_info(updated_tools_info):
    """Save updated tool information to a file or database"""
    logging.info("save_updated_tools")
    """Saves updated tools information to a JSON file."""
    try:
        # 确定文件路径，确保不使用 JSON 数据作为文件名
        output_file_path = DATABANK_FILE
        
        # 将更新后的工具信息保存为 JSON 文件
        with open(output_file_path, 'w') as f:
            json.dump(updated_tools_info, f, indent=4)
        
        logging.info(f"Updated tools information saved to {output_file_path}")
        
        update_databank(updated_tools_info)
        logging.info("saved tools into csv now update the tools")

    except Exception as e:
        logging.error(f"Error occurred while saving updated tools info: {e}")
    #pass

def main():
    logging.info("Starting main function...")
    video_folder = "/mnt/IndEgo_Aria/bosong/video_clip90/"
    video_files = find_and_sort_mp4_files(video_folder)

    for video_path in video_files:
        process_video(video_path)

    logging.info("Main function completed.")

if __name__ == "__main__":
    main()