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

def enhance_illumination(img_rgb: np.ndarray) -> np.ndarray:
    """
    Cân bằng sáng cục bộ CLAHE trên kênh L (không làm biến đổi màu sắc tự nhiên),
    giúp trích xuất 128-d face encoding và 68 landmarks ổn định khi lớp học thiếu sáng/ngược sáng.
    """
    lab = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl = clahe.apply(l_channel)
    merged = cv2.merge((cl, a_channel, b_channel))
    return cv2.cvtColor(merged, cv2.COLOR_LAB2RGB)

def process_face_pipeline(base64_str: str, num_jitters: int = 1):
    """
    Trả về: (status, face_crop, face_encoding, landmarks)
    status: "NO_FACE", "MULTIPLE_FACES", "SUCCESS"
    """
    img_rgb = decode_base64(base64_str)
    if img_rgb is None:
        return "NO_FACE", None, None, {}

    h, w, _ = img_rgb.shape
    img_enhanced = enhance_illumination(img_rgb)

    # 1. Tìm mặt tốc độ cao ở tỉ lệ 0.5x trước
    small_img = cv2.resize(img_enhanced, (0, 0), fx=0.5, fy=0.5)
    face_locations_small = face_recognition.face_locations(small_img, model="hog")

    if len(face_locations_small) > 1:
        return "MULTIPLE_FACES", None, None, {}

    if len(face_locations_small) == 1:
        top_s, right_s, bottom_s, left_s = face_locations_small[0]
        top = max(0, top_s * 2)
        right = min(w, right_s * 2)
        bottom = min(h, bottom_s * 2)
        left = max(0, left_s * 2)
    else:
        # Fallback: Nếu sinh viên đứng hơi xa (0.5x làm mặt quá nhỏ), quét trên ảnh gốc 1.0x
        face_locations_full = face_recognition.face_locations(img_enhanced, number_of_times_to_upsample=1, model="hog")
        if len(face_locations_full) == 0:
            return "NO_FACE", None, None, {}
        if len(face_locations_full) > 1:
            return "MULTIPLE_FACES", None, None, {}
        top, right, bottom, left = face_locations_full[0]

    # Kiểm tra kích thước mặt tối thiểu để tránh nhận diện nhiễu ở quá xa
    if (bottom - top) < 40 or (right - left) < 40:
        return "NO_FACE", None, None, {}

    # 2. Cắt ảnh trên img_rgb gốc (chưa qua CLAHE) để giữ nguyên đặc trưng quang học cho Liveness
    face_crop = img_rgb[top:bottom, left:right]

    # 3. Trích xuất 128-d vector trên ảnh đã cân bằng sáng CLAHE
    face_locations = [(top, right, bottom, left)]
    encodings = face_recognition.face_encodings(img_enhanced, face_locations, num_jitters=num_jitters)
    if not encodings:
        return "NO_FACE", None, None, {}
    face_encoding = encodings[0].tolist()

    # 4. Trích xuất 68 điểm mốc khuôn mặt
    landmarks_list = face_recognition.face_landmarks(img_enhanced, face_locations)
    landmarks = landmarks_list[0] if landmarks_list else {}

    return "SUCCESS", face_crop, face_encoding, landmarks