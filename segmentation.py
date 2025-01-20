import json
from moviepy.video.io.VideoFileClip import VideoFileClip
import os

# Paths
video_path = '/mnt/logicNAS/Exchange/Aria/User_16/video/User_16_414_0511_2_480.mp4'
annotation_path = '/mnt/logicNAS/Exchange/Aria/User_16/video/User_16_414_0511_2_480.json'
output_video_path = '/mnt/logicNAS/Exchange/Aria/User_16/video_seg_90/'
output_annotation_path = '/mnt/logicNAS/Exchange/Aria/User_16/video_seg_90/'

# Load annotations
with open(annotation_path, 'r') as f:
    data = json.load(f)

# Extract metadata
metadata = data['metadata']

# Helper function to create output directories if they don't exist
os.makedirs(output_video_path, exist_ok=True)
os.makedirs(output_annotation_path, exist_ok=True)

# Process annotations and cut video
video_clips = []
current_start = 0
clip_counter = 1
current_annotations = []

for meta_id, meta_info in metadata.items():
    start, end = meta_info['z']
    annotation_text = meta_info['av']['1']

    if end - current_start > 90:
        # Save current clip and annotations
        clip_name = f'clip_{clip_counter}.mp4'
        annotation_name = f'clip_{clip_counter}.json'
        
        # Load the video
        with VideoFileClip(video_path) as video:
            video_subclip = video.subclipped(current_start, start)
            video_subclip.write_videofile(os.path.join(output_video_path, clip_name), codec='libx264')
        
        # Save annotations
        with open(os.path.join(output_annotation_path, annotation_name), 'w') as f:
            json.dump(current_annotations, f)
        
        # Update for next clip
        current_start = start
        clip_counter += 1
        current_annotations = []

    # Add current annotation to the current list
    current_annotations.append({
        "start": start,
        "end": end,
        "annotation": annotation_text
    })

# Ensure the last segment is saved
if current_annotations:
    clip_name = f'clip_{clip_counter}.mp4'
    annotation_name = f'clip_{clip_counter}.json'
    
    with VideoFileClip(video_path) as video:
        video_subclip = video.subclipped(current_start, video.duration)
        video_subclip.write_videofile(os.path.join(output_video_path, clip_name), codec='libx264')
    
    with open(os.path.join(output_annotation_path, annotation_name), 'w') as f:
        json.dump(current_annotations, f)

print("Video splitting and annotation saving completed.")
