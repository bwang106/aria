import cv2
import numpy as np

def process_video(video_path):
    # 打开视频文件
    cap = cv2.VideoCapture(video_path)
    fgbg = cv2.createBackgroundSubtractorMOG2()

    key_frames = []
    prev_frame_time = 0
    frame_time = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # 转换为灰度图像
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        fgmask = fgbg.apply(gray)

        # 识别动态前景
        motion = cv2.countNonZero(fgmask)

        # 获取当前帧时间戳
        frame_time = cap.get(cv2.CAP_PROP_POS_MSEC)

        # 判断运动减少并持续超过0.5秒
        if motion < 2000 and (frame_time - prev_frame_time) > 500:
            key_frames.append(frame)
            prev_frame_time = frame_time
            print(f"Key frame detected at {frame_time} ms")

        # 显示处理后的帧
        cv2.imshow('Frame', frame)
        if cv2.waitKey(30) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

    return key_frames

video_path = 'your_first_person_video.mp4'
key_frames = process_video(video_path)
print(f"Total key frames detected: {len(key_frames)}")