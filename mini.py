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
RESULT_BASE_PATH = "/mnt/Data/bosong/agent/test"


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
    logging.info("")  # 为了更好的可读性添加换行

# Create the model
generation_config = {
    "temperature": 0.2,#
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
    model_name="gemini-2.0-flash-exp",
    generation_config=generation_config,
)

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

# Main function
def main():
    logging.info("Starting main function...")
    video_folder = "/mnt/logicNAS/Exchange/Aria/User_16/video_seg_90/"  #change

    # Get and sort the MP4 files
    video_files = find_and_sort_mp4_files(video_folder)
    

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
                        """
                        go through whole video and tell me if there is a Using sandpaper to smooth the edges of the block task and when does start and end time. If no, then show nothing.
                        and also tells me the name of the video file.
                        """],
                },
            ]
        )

        # Send the message to Gemini
        logging.info("Sending message to Gemini...")
        response = chat_session.send_message("Extract  information from the videos.")

        # Save Gemini's output
        save_gemini_output(response.text)

        #check if response is empty before parsing
        if not response.text:
            logging.warning("Received empty response from Gemini.")
            continue #skip to next video
        

    
    logging.info("Main function completed.")

if __name__ == "__main__":
    main()