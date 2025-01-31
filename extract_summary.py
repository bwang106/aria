import os
import pandas as pd
import csv
import gemini_tools

# 定义文件路径
#RESULT_BASE_PATH = "/mnt/Data/bosong/agent/result_gemini-2.0-flash-exp"

INPUT_CSV_FILE = os.path.join(gemini_tools.RESULT_BASE_PATH, "gemini_output.csv")
OUTPUT_CSV_FILE = os.path.join(gemini_tools.RESULT_BASE_PATH, "task_summaries_output.csv")
INPUT_TXT_FILE = os.path.join(gemini_tools.RESULT_BASE_PATH, "gemini_output.txt")

def convert_to_txt(csv_file, txt_file):
    """将 CSV 文件转换为 TXT 文件。"""
    try:
        df = pd.read_csv(csv_file, header=None, encoding='utf-8-sig', quotechar='"', skipinitialspace=True, on_bad_lines='skip')
        print("CSV file read successfully.")
        
        # 写入 TXT 文件
        df.to_csv(txt_file, index=False, header=False, encoding='utf-8-sig', sep='\t', lineterminator='\n')
        print(f"CSV file converted to TXT: {txt_file}")
    except Exception as e:
        print(f"An error occurred while converting the CSV file to TXT: {str(e)}")  

def clean_line(line):
    """清理行中的特殊字符。"""
    special_chars = ["`", "‘", "’", "{", "}", "[", "]", '"']
    for char in special_chars:
        line = line.replace(char, "")
    return line.strip()

def extract_task_summaries(txt_file):
    """从 TXT 文件中提取任务总结并按顺序返回。"""
    if not os.path.exists(txt_file):
        print("TXT file does not exist")
        return []

    summaries = []
    try:
        with open(txt_file, 'r', encoding='utf-8') as file:
            print("TXT file read successfully.")
            current_summary = []
            recording = False
            
            for line in file:
                line = line.strip()
                if not line:
                    continue
                
                line = clean_line(line)

                if "Task Summary:" in line:
                    recording = True
                    current_summary.append(line)
                elif "End Summary." in line and recording:
                    current_summary.append(line)
                    summaries.append("\n".join(current_summary))
                    current_summary = []
                    recording = False
                elif recording:
                    current_summary.append(line)
                
        return summaries
    except Exception as e:
        print(f"An error occurred while reading the TXT file: {str(e)}")
        return []

def save_task_summaries(summaries, output_csv_file):
    """将提取的任务总结保存到新的 CSV 文件。"""
    try:
        if summaries:
            with open(output_csv_file, mode='w', encoding='utf-8-sig', newline='') as file:
                writer = csv.writer(file)  # 创建 CSV 写入对象
                for summary in summaries:
                    writer.writerow([summary])  # 将每个总结作为一行写入 CSV 文件
            print(f"Task summaries saved to {output_csv_file}")
        else:
            print("No task summaries to save.")
    except Exception as e:
        print(f"An error occurred while saving the task summaries: {str(e)}")

def main():
    convert_to_txt(INPUT_CSV_FILE, INPUT_TXT_FILE)
    task_summaries = extract_task_summaries(INPUT_TXT_FILE)

    if task_summaries:
        save_task_summaries(task_summaries, OUTPUT_CSV_FILE)
    else:
        print("No task summaries to save.")

if __name__ == "__main__":
    main()