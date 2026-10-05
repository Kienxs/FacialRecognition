# ai_service/face_engine.py
import base64
import cv2
import numpy as np
import face_recognition

def decode_base64(base64_str: str):
    if "," in base64_str:
        base64_str = base64_str.split(",")[1]
    img_data = base64.b64decode(base64_str)
    np_arr = np.frombuffer(img_data, np.uint8)
    img_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    return cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

def process_face_pipeline(base64_str: str):
    """
    Trả về: (status, face_crop, face_encoding)
    status: "NO_FACE", "MULTIPLE_FACES", "SUCCESS"
    """
    img_rgb = decode_base64(base64_str)
    face_locations = face_recognition.face_locations(img_rgb)
    
    if len(face_locations) == 0:
        return "NO_FACE", None, None
        
    if len(face_locations) > 1:
        return "MULTIPLE_FACES", None, None
        
    # Crop khuôn mặt để gửi cho module Liveness
    top, right, bottom, left = face_locations[0]
    # Mở rộng bounding box một chút để bắt được cấu trúc viền khuôn mặt (tuỳ chọn)
    face_crop = img_rgb[top:bottom, left:right]
    
    face_encoding = face_recognition.face_encodings(img_rgb, face_locations)[0].tolist()
    
    return "SUCCESS", face_crop, face_encoding