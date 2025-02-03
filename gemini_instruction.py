import csv
import os
import time
import logging
import google.generativeai as genai
# from config import GEMINI_API_KEY # Assuming config.py is in the same directory or PYTHONPATH
import pandas as pd
import re
import sys
import json
from datetime import datetime

# --- Configuration ---
MEMORY_FOLDER = "/mnt/logicNAS/Exchange/bosong/memory/"
DATABANK_FILE = os.path.join(MEMORY_FOLDER, "databank.csv") # Initial databank file (can be updated)
CSV_FILE = os.path.join(MEMORY_FOLDER, "newtask_output.csv")
VIDEO_FOLDER = "/mnt/logicNAS/Exchange/bosong/" # Folder to read video from
MODEL_NAME = "gemini-2.0-flash-exp"
GEMINI_PARAMS = {
    "temperature": 0.2,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 12000,
}
# GEMINI_API_KEY = "YOUR_API_KEY_HERE" # Replace with your actual API key or uncomment config import if you have config.py

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(MEMORY_FOLDER, "gemini_agent.log")), # Log file in memory folder
        logging.StreamHandler()
    ]
)

# Configure Gemini API
# genai.configure(api_key=GEMINI_API_KEY) # Uncomment and set your API key
# model = genai.GenerativeModel(model_name=MODEL_NAME) # Initialize Gemini model globally - uncomment if you initialize globally

# --- Memory Bank Functions ---
def read_memory_bank(memory_folder):
    """
    Reads all CSV files from the memory folder and returns a list of task data.
    Each task data is a list of rows from a CSV file.
    """
    memory_data = {}
    if not os.path.exists(memory_folder):
        os.makedirs(memory_folder)  # Create folder if it doesn't exist
        logging.info(f"Memory folder created: {memory_folder}")
        return memory_data # Return empty dict if folder is newly created

    all_task_data = [] # List to hold all task data for combined context
    for filename in os.listdir(memory_folder):
        if filename.endswith(".csv"):
            task_name = filename[:-4]  # Remove ".csv" extension for task name
            filepath = os.path.join(memory_folder, filename)
            task_data = []
            try:
                with open(filepath, 'r', newline='') as csvfile:
                    csv_reader = csv.reader(csvfile)
                    header = next(csv_reader, None) # Read header row if exists
                    if header:
                        task_data.append(header) # Include header in task data
                    for row in csv_reader:
                        task_data.append(row)
                        all_task_data.append(row) # Collect all rows for combined memory
                memory_data[task_name] = task_data
                logging.info(f"Memory bank loaded from: {filename}")
            except Exception as e:
                logging.error(f"Error reading CSV file {filename}: {e}")
    return memory_data, all_task_data # Return both task-wise and combined data

def write_memory_bank(memory_folder, task_name, task_data):
    """
    Writes task data to a new CSV file in the memory folder.
    Filename includes task name and timestamp.
    """
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{task_name}_{timestamp_str}.csv"
    filepath = os.path.join(memory_folder, filename)

    try:
        with open(filepath, 'w', newline='') as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerows(task_data)
        logging.info(f"New databank saved to: {filepath}")
        return filepath
    except Exception as e:
        logging.error(f"Error writing to CSV file {filename}: {e}")
        return None

# --- Action Recording and Analysis Functions ---
def record_action(csv_writer, task_data, timestamp, action, tool, tool_location=None, tool_status=None):
    """
    Records a user action with timestamp, tool, and optional tool location/status.
    Appends the action as a row to the task_data list and writes to CSV.
    """
    action_row = [timestamp, action, tool, tool_location if tool_location else "", tool_status if tool_status else ""]
    task_data.append(action_row)
    csv_writer.writerow(action_row) # Write to CSV
    logging.info(f"Action recorded and written to CSV: {action_row}")


# --- Video Processing Function ---
def process_video(video_path, csv_writer, task_data, model, memory_data_combined):
    """Processes a single video and extracts actions using Gemini API, considering databank."""
    logging.info(f"Processing video file using Gemini API with databank context: {video_path}")

    try:
        # --- Prepare video part for Gemini API (Corrected method - read binary) ---
        with open(video_path, 'rb') as video_file: # Open video file in binary read mode
            video_data = video_file.read() # Read video file content as bytes
        video_part = {"mime_type": "video/mp4", "data": video_data}

        # --- Construct Gemini Prompt with Databank Context ---
        databank_context = ""
        if memory_data_combined:
            databank_context = "Here are actions from my past tasks:\n"
            for row in memory_data_combined:
                if len(row) > 2: # Basic check to avoid index errors
                    databank_context += f"- [{row[0]}] {row[1]} using {row[2]}\n" # Simple format, can be improved

        prompt_text = f"""Analyze the user's actions in this video.
        Identify each action, the tool being used, and provide a timestamp for each action.
        If possible, also identify the location of the tool and the status of the tool if it's relevant.
        Consider my past task experiences when analyzing this video.
        {databank_context}
        Return the output in a comma-separated format for each action:
        'timestamp, action, tool, tool_location, tool_status'
        If tool_location or tool_status is not identified, leave those fields empty.
        """

        # --- Call Gemini API for video analysis ---
        responses = model.generate_content(
            model=MODEL_NAME,
            contents=[video_part, prompt_text], # Video and text prompt as content
            generation_config=GEMINI_PARAMS
        )

        gemini_response_text = responses.text # Get text response from Gemini

        if gemini_response_text:
            # --- Parse Gemini Response (assuming CSV-like format) ---
            action_lines = gemini_response_text.strip().split('\n') # Split response into lines
            logging.info(f"Gemini API Response received and parsing started. Response:\n{gemini_response_text}")

            for response_line in action_lines:
                try:
                    parts = response_line.split(',')
                    timestamp = parts[0].strip() if len(parts) > 0 else ""
                    action = parts[1].strip() if len(parts) > 1 else ""
                    tool = parts[2].strip() if len(parts) > 2 else ""
                    tool_location = parts[3].strip() if len(parts) > 3 else None # Allow empty location
                    tool_status = parts[4].strip() if len(parts) > 4 else None   # Allow empty status

                    record_action(csv_writer, task_data, timestamp, action, tool, tool_location, tool_status)

                except Exception as parse_err:
                    logging.error(f"Error parsing Gemini response line: {response_line}. Error: {parse_err}")
        else:
            logging.warning("Gemini API returned an empty response for video analysis.")


    except Exception as api_err:
        logging.error(f"Error during Gemini API call for video analysis: {api_err}")

    logging.info(f"Video processing with Gemini API and databank context complete for: {video_path}")


# --- Instruction Generation and Experience Functions ---
def generate_instructions_from_memory(csv_writer, memory_folder, task_query):
    """
    Searches the memory bank for tasks related to the task_query.
    Generates instructions based on the most relevant task found and writes to CSV.
    (Simple keyword matching for now, can be improved with more sophisticated semantic search)
    """
    memory_data, _ = read_memory_bank(memory_folder) # Only need task-wise data for instructions
    relevant_tasks = {}

    for task_name, task_data in memory_data.items():
        if task_query.lower() in task_name.lower(): # Simple keyword search in task name
            relevant_tasks[task_name] = task_data

    if not relevant_tasks:
        instruction_message = "No similar tasks found in memory. Please perform the task and I will record it for future reference."
        csv_writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Instruction Generation", instruction_message]) # Write to CSV
        logging.info(instruction_message)
        return instruction_message

    best_task_name = list(relevant_tasks.keys())[0] # Take the first relevant task for simplicity
    best_task_data = relevant_tasks[best_task_name]

    instructions = f"Instructions for '{task_query}' based on previous experience with '{best_task_name}':\n"
    if best_task_data and len(best_task_data) > 1: # Check if task data is not empty and has action rows (skip header if present)
        header = best_task_data[0] if best_task_data[0] and isinstance(best_task_data[0], list) and len(best_task_data[0]) > 1 and header_check(best_task_data[0]) else None # Check if first row looks like header
        start_row_index = 1 if header else 0 # Start from 1 if header exists, otherwise 0

        instructions += f"Tools Used: {', '.join(set([row[2] for row in best_task_data[start_row_index:] if len(row) > 2]))}\n" # Extract unique tools
        instructions += "Steps:\n"
        for i, action_row in enumerate(best_task_data[start_row_index:]):
            if len(action_row) > 2: # Ensure row has enough elements
                timestamp, action, tool = action_row[0], action_row[1], action_row[2]
                instructions += f"  {i+1}. [{timestamp}] {action} using {tool}"
                if len(action_row) > 3 and action_row[3]:
                    instructions += f" at {action_row[3]}"
                if len(action_row) > 4 and action_row[4]:
                    instructions += f" (Status: {action_row[4]})"
                instructions += "\n"
    else:
        instructions = f"No detailed steps recorded for '{best_task_name}'. Tools used might be: {', '.join(set([row[2] for row in best_task_data[1:] if len(row) > 2])) if best_task_data and len(best_task_data) > 1 else 'Unknown'}"

    csv_writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Instructions", instructions]) # Write instructions to CSV
    logging.info("Instructions generated and written to CSV.")
    return instructions

def summarize_experience(csv_writer, task_data, model): # Added model as argument
    """
    Summarizes the experience from the recorded task data and writes to CSV using Gemini.
    """
    if not task_data or len(task_data) <= 1: # Check if task_data is empty or only header
        summary_message = "No actions recorded for this task yet."
        csv_writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Summary", summary_message]) # Write to CSV
        logging.info(summary_message)
        return summary_message

    tools_used = set()
    actions_count = 0
    action_list_for_prompt = [] # Prepare action list for prompt
    for row in task_data[1:]: # Skip header row
        if len(row) > 2:
            tools_used.add(row[2])
            actions_count += 1
            action_list_for_prompt.append(f"[{row[0]}] {row[1]} using {row[2]}{' at ' + row[3] if row[3] else ''}{' (Status: ' + row[4] + ')' if row[4] else ''}")

    summary_prefix = "Task Summary:\n"
    summary_prefix += f"  Tools used: {', '.join(tools_used) if tools_used else 'None'}\n"
    summary_prefix += f"  Number of actions performed: {actions_count}\n"
    summary_prefix += "  Task completed successfully (based on recorded actions).\n\n"

    try:
        # --- Gemini Model for Experience Summarization (Real Application) ---
        prompt_text = f"Summarize the experience of performing the following task. Provide a concise and insightful summary, highlighting any challenges, successes, or key observations.  Here are the actions performed:\n{chr(10).join(action_list_for_prompt)}" # Use newline for better readability in prompt

        response = model.generate_content(
            prompt_text,
            generation_config=GEMINI_PARAMS # Use generation_config instead of parameters for gemini-pro
        )
        gemini_summary = response.text
        detailed_summary = f"{summary_prefix}Detailed Summary from Gemini:\n{gemini_summary}"
        logging.info(f"--- Gemini Experience Summarization using {MODEL_NAME} ---")

    except Exception as e:
        logging.error(f"Error during Gemini experience summarization: {e}")
        detailed_summary = f"{summary_prefix}Error generating detailed summary from Gemini. Basic summary provided."

    csv_writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Summary", detailed_summary]) # Write detailed summary to CSV
    logging.info("Task summary generated and written to CSV (including Gemini summary).")
    return detailed_summary

def header_check(row):
    """Simple heuristic to check if a row is likely a header row based on content type"""
    if not row:
        return False
    return all(isinstance(item, str) for item in row) # Assume header row contains only strings


# --- Main Execution / Example Usage ---
if __name__ == "__main__":
    task_name = "MakingCoffeeFromVideo" # Updated task name for video processing
    task_data = [["Timestamp", "Action", "Tool", "Tool Location", "Tool Status"]] # Initialize with header row

    logging.info(f"--- Starting Task: {task_name} (Video Processing with Databank Integration) ---")

    # --- Initialize CSV file for output log ---
    try:
        csvfile = open(CSV_FILE, 'w', newline='') # Open in write mode to create/overwrite
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(["Log Timestamp", "Type", "Content"]) # Write a general header for the log CSV
        csv_writer.writerow(["Timestamp", "Action", "Tool", "Tool Location", "Tool Status"]) # Write action header
    except Exception as e:
        logging.error(f"Error opening CSV file {CSV_FILE} for writing: {e}")
        sys.exit(1)

    # --- Initialize Gemini Model ---
    try:
        genai.configure(api_key="YOUR_API_KEY_HERE") # Replace with your actual API key
        model = genai.GenerativeModel(model_name=MODEL_NAME) # Initialize Gemini model here
        logging.info(f"Gemini model '{MODEL_NAME}' initialized successfully.")
    except Exception as e:
        logging.error(f"Error initializing Gemini model: {e}. Please check your API key and network connection.")
        csv_writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Error", f"Gemini Initialization Failed: {e}"])
        csvfile.close()
        sys.exit(1)

    # --- Read Existing Memory Bank ---
    memory_data_taskwise, memory_data_combined = read_memory_bank(MEMORY_FOLDER) # Get both types of memory data

    # --- Get Video Path from User (or you can hardcode for testing) ---
    video_filename = input(f"Enter video filename from '{VIDEO_FOLDER}' (e.g., myvideo.mp4): ") # Prompt for video file
    video_path = os.path.join(VIDEO_FOLDER, video_filename)

    if not os.path.exists(video_path):
        logging.error(f"Video file not found: {video_path}")
        print(f"Error: Video file not found: {video_path}") # Print to console as well for user feedback
        csvfile.close()
        sys.exit(1)

    # --- Process Video using Gemini API with Databank Context ---
    process_video(video_path, csv_writer, task_data, model, memory_data_combined) # Pass combined memory data

    # --- Prepare New Databank Task Data (including header and new actions) ---
    new_databank_task_data = [["Timestamp", "Action", "Tool", "Tool Location", "Tool Status"]] + task_data[1:] # Include header and actions from current task

    # --- Save New Databank to Memory Bank (overwriting or creating new) ---
    new_databank_filepath = write_memory_bank(MEMORY_FOLDER, task_name + "_databank", new_databank_task_data) # New databank filename

    # --- Write Summary and Instructions to the output CSV ---
    if new_databank_filepath: # Check if databank was saved successfully (important for summary/instructions based on new data)
        logging.info(f"\n--- Task '{task_name}' (Video) Completed, New Databank Saved ---")
        summarize_experience(csv_writer, task_data, model) # Pass csv_writer and model (summarize based on current task actions)
        logging.info("Task summary written to CSV (including Gemini summary).")

        # --- Example: Future User asking for instructions (using potentially updated memory) ---
        logging.info("\n--- Future User Requesting Instructions (from potentially updated memory) ---")
        instruction_query = "How to make coffee" # Or a more general query like "Perform the task in the video"
        generate_instructions_from_memory(csv_writer, MEMORY_FOLDER, instruction_query) # Pass csv_writer
        logging.info("Instructions written to CSV.")

    else:
        logging.error("New databank was not saved to memory due to an error.")

    # --- Close CSV file ---
    csvfile.close()
    logging.info(f"CSV file closed: {CSV_FILE}")
    logging.info(f"--- Task '{task_name}' (Video) Processing Finished ---")