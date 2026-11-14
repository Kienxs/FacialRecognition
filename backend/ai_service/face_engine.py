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

def enhance_contrast(img_rgb):
    """Tăng cường độ tương phản tự nhiên (CLAHE) để phát hiện mặt trong điều kiện thiếu sáng hoặc bóng tối"""
    try:
        lab = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        limg = cv2.merge((cl, a, b))
        return cv2.cvtColor(limg, cv2.COLOR_LAB2RGB)
    except Exception:
        return img_rgb

def detect_face_locations_robust(img_rgb):
    """
    Chiến lược phát hiện khuôn mặt tốc độ cao + đa cấp độ (High-speed Multi-stage):
    1. Quét trực tiếp trên ảnh với upsample=0 (siêu nhanh ~0.03s trên CPU)
    2. Quét nhanh trên ảnh thu nhỏ 0.5 (~0.02s)
    3. Thử tăng cường tương phản CLAHE upsample=0 (xử lý bóng mờ / đèn hắt ~0.04s)
    4. Thử lật gương + CLAHE upsample=0 (xử lý webcam lật gương ~0.04s)
    5. Fallback cuối cùng: upsample=1 trên ảnh gốc (nếu mặt quá nhỏ)
    """
    # 1. Quét trực tiếp ảnh gốc không upsample (cực nhanh và bắt đúng kích cỡ khuôn mặt chuẩn)
    locs = face_recognition.face_locations(img_rgb, number_of_times_to_upsample=0, model="hog")
    if len(locs) >= 1:
        return locs

    # 2. Thử trên ảnh thu nhỏ 0.5
    small_img = cv2.resize(img_rgb, (0, 0), fx=0.5, fy=0.5)
    locs_s = face_recognition.face_locations(small_img, number_of_times_to_upsample=0, model="hog")
    if len(locs_s) == 1:
        top_s, right_s, bottom_s, left_s = locs_s[0]
        return [(top_s * 2, right_s * 2, bottom_s * 2, left_s * 2)]
    if len(locs_s) > 1:
        return [(t * 2, r * 2, b * 2, l * 2) for (t, r, b, l) in locs_s]

    # 3. Tăng cường tương phản CLAHE (bù sáng bóng râm phòng/đeo kính)
    enhanced = enhance_contrast(img_rgb)
    locs_enh = face_recognition.face_locations(enhanced, number_of_times_to_upsample=0, model="hog")
    if len(locs_enh) >= 1:
        return locs_enh

    # 4. Thử lật gương có tăng tương phản
    flipped = cv2.flip(img_rgb, 1)
    enhanced_f = enhance_contrast(flipped)
    locs_f = face_recognition.face_locations(enhanced_f, number_of_times_to_upsample=0, model="hog")
    if len(locs_f) >= 1:
        W = img_rgb.shape[1]
        return [(top_f, W - left_f, bottom_f, W - right_f) for (top_f, right_f, bottom_f, left_f) in locs_f]

    # 5. Fallback cuối: upsample=1 cho trường hợp mặt quá xa camera
    locs_up1 = face_recognition.face_locations(img_rgb, number_of_times_to_upsample=1, model="hog")
    if len(locs_up1) >= 1:
        return locs_up1

    # 6. Fallback tuyệt đối bằng CNN (chuyên trị góc nghiêng mạnh, đeo kính cận, bóng tối)
    try:
        small_cnn = cv2.resize(img_rgb, (0, 0), fx=0.5, fy=0.5)
        locs_cnn = face_recognition.face_locations(small_cnn, number_of_times_to_upsample=0, model="cnn")
        if len(locs_cnn) >= 1:
            top_s, right_s, bottom_s, left_s = locs_cnn[0]
            return [(top_s * 2, right_s * 2, bottom_s * 2, left_s * 2)]
    except Exception:
        pass

    return []

def process_face_pipeline(base64_str: str):
    """
    Trả về: (status, face_crop, face_encoding, landmarks)
    status: "NO_FACE", "MULTIPLE_FACES", "SUCCESS"
    """
    img_rgb = decode_base64(base64_str)
    if img_rgb is None:
        return "NO_FACE", None, None, {}
    
    face_locations = detect_face_locations_robust(img_rgb)
    
    if len(face_locations) == 0:
        return "NO_FACE", None, None, {}
        
    if len(face_locations) > 1:
        return "MULTIPLE_FACES", None, None, {}
        
    top, right, bottom, left = face_locations[0]
    h, w, _ = img_rgb.shape
    top = max(0, min(h, top))
    bottom = max(0, min(h, bottom))
    left = max(0, min(w, left))
    right = max(0, min(w, right))
    
    if bottom <= top or right <= left:
        return "NO_FACE", None, None, {}
        
    face_crop = img_rgb[top:bottom, left:right]
    
    # Trích xuất vector embedding và 68 điểm landmarks
    face_locations_orig = [(top, right, bottom, left)]
    encodings = face_recognition.face_encodings(img_rgb, face_locations_orig)
    if not encodings:
        return "NO_FACE", None, None, {}
        
    face_encoding = encodings[0].tolist()
    landmarks_list = face_recognition.face_landmarks(img_rgb, face_locations_orig)
    landmarks = landmarks_list[0] if landmarks_list else {}
    
    return "SUCCESS", face_crop, face_encoding, landmarks
