# ai_service/face_engine.py
import base64
import cv2
import numpy as np
import face_recognition

def decode_base64(base64_str: str):
    try:
        if "," in base64_str:
            base64_str = base64_str.split(",")[1]
        img_data = base64.b64decode(base64_str)
        np_arr = np.frombuffer(img_data, np.uint8)
        img_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img_bgr is None or img_bgr.size == 0:
            return None
        return cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    except Exception:
        return None

def process_face_pipeline(base64_str: str):
    """
    Trả về: (status, face_crop, face_encoding, landmarks)
    status: "NO_FACE", "MULTIPLE_FACES", "SUCCESS"
    Tối ưu tốc độ xử lý dưới 0.15s trên CPU.
    """
    img_rgb = decode_base64(base64_str)
    if img_rgb is None:
        return "NO_FACE", None, None, {}
    
    # 1. Thu nhỏ ảnh tỉ lệ 0.5 để thuật toán HOG tìm vị trí mặt nhanh gấp 4 lần
    small_img = cv2.resize(img_rgb, (0, 0), fx=0.5, fy=0.5)
    face_locations_small = face_recognition.face_locations(small_img, model="hog")
    
    if len(face_locations_small) == 0:
        return "NO_FACE", None, None, {}
        
    if len(face_locations_small) > 1:
        return "MULTIPLE_FACES", None, None, {}
        
    # 2. Quy đổi tọa độ về kích thước ảnh gốc
    top_s, right_s, bottom_s, left_s = face_locations_small[0]
    h, w, _ = img_rgb.shape
    top = max(0, top_s * 2)
    right = min(w, right_s * 2)
    bottom = min(h, bottom_s * 2)
    left = max(0, left_s * 2)
    
    face_crop = img_rgb[top:bottom, left:right]
    
    # 3. Trích xuất 128-d vector embedding chính xác tuyệt đối trên ảnh gốc
    face_locations = [(top, right, bottom, left)]
    face_encoding = face_recognition.face_encodings(img_rgb, face_locations)[0].tolist()
    
    # 4. Trích xuất 68 điểm mốc khuôn mặt phục vụ kiểm tra cử động sống (Blink & Motion Dynamics)
    landmarks_list = face_recognition.face_landmarks(img_rgb, face_locations)
    landmarks = landmarks_list[0] if landmarks_list else {}
    
    return "SUCCESS", face_crop, face_encoding, landmarks
