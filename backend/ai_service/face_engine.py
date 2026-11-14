import cv2
import numpy as np
import base64
import face_recognition

def decode_base64(base64_str: str):
    """Giải mã chuỗi Base64 sang NumPy Array (RGB)"""
    try:
        if "," in base64_str:
            base64_str = base64_str.split(",")[1]
        img_bytes = base64.b64decode(base64_str)
        nparr = np.frombuffer(img_bytes, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
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
    try:
        lab = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l_channel)
        merged = cv2.merge((cl, a_channel, b_channel))
        return cv2.cvtColor(merged, cv2.COLOR_LAB2RGB)
    except Exception:
        return img_rgb

def detect_face_locations_robust(img_rgb: np.ndarray):
    """
    Chiến lược phát hiện khuôn mặt tốc độ cao + đa cấp độ (High-speed Multi-stage):
    1. Quét nhanh trên ảnh thu nhỏ 0.5 (~0.02s)
    2. Quét trực tiếp ảnh với upsample=0
    3. Quét upsample=1 trên ảnh gốc (nếu mặt ở xa)
    4. Thử lật gương webcam
    5. Fallback CNN (nếu có dlib mmod cnn)
    """
    h, w, _ = img_rgb.shape

    # 1. Thử trên ảnh thu nhỏ 0.5 (nhanh nhất)
    small_img = cv2.resize(img_rgb, (0, 0), fx=0.5, fy=0.5)
    locs_s = face_recognition.face_locations(small_img, number_of_times_to_upsample=0, model="hog")
    if len(locs_s) == 1:
        top_s, right_s, bottom_s, left_s = locs_s[0]
        return [(top_s * 2, min(w, right_s * 2), min(h, bottom_s * 2), left_s * 2)]
    if len(locs_s) > 1:
        return [(t * 2, min(w, r * 2), min(h, b * 2), l * 2) for (t, r, b, l) in locs_s]

    # 2. Quét trực tiếp ảnh gốc không upsample
    locs = face_recognition.face_locations(img_rgb, number_of_times_to_upsample=0, model="hog")
    if len(locs) >= 1:
        return locs

    # 3. Fallback upsample=1 cho trường hợp mặt xa camera
    locs_up1 = face_recognition.face_locations(img_rgb, number_of_times_to_upsample=1, model="hog")
    if len(locs_up1) >= 1:
        return locs_up1

    # 4. Thử lật gương
    flipped = cv2.flip(img_rgb, 1)
    locs_f = face_recognition.face_locations(flipped, number_of_times_to_upsample=0, model="hog")
    if len(locs_f) >= 1:
        return [(top_f, w - left_f, bottom_f, w - right_f) for (top_f, right_f, bottom_f, left_f) in locs_f]

    # 5. Fallback tuyệt đối bằng CNN (chuyên trị góc nghiêng mạnh, đeo kính cận)
    try:
        locs_cnn = face_recognition.face_locations(small_img, number_of_times_to_upsample=0, model="cnn")
        if len(locs_cnn) >= 1:
            top_s, right_s, bottom_s, left_s = locs_cnn[0]
            return [(top_s * 2, min(w, right_s * 2), min(h, bottom_s * 2), left_s * 2)]
    except Exception:
        pass

    return []

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

    face_locations = detect_face_locations_robust(img_enhanced)
    if len(face_locations) == 0:
        return "NO_FACE", None, None, {}
    if len(face_locations) > 1:
        return "MULTIPLE_FACES", None, None, {}

    top, right, bottom, left = face_locations[0]
    top = max(0, min(h, top))
    bottom = max(0, min(h, bottom))
    left = max(0, min(w, left))
    right = max(0, min(w, right))

    # Kiểm tra kích thước mặt tối thiểu để tránh nhận diện nhiễu ở quá xa
    if (bottom - top) < 40 or (right - left) < 40:
        return "NO_FACE", None, None, {}

    # Cắt ảnh trên img_rgb gốc (chưa qua CLAHE) để giữ nguyên đặc trưng quang học cho Liveness
    face_crop = img_rgb[top:bottom, left:right]

    # Trích xuất 128-d vector trên ảnh đã cân bằng sáng CLAHE
    target_locs = [(top, right, bottom, left)]
    encodings = face_recognition.face_encodings(img_enhanced, target_locs, num_jitters=num_jitters)
    if not encodings:
        return "NO_FACE", None, None, {}
    face_encoding = encodings[0].tolist()

    # Trích xuất 68 điểm mốc khuôn mặt
    landmarks_list = face_recognition.face_landmarks(img_enhanced, target_locs)
    landmarks = landmarks_list[0] if landmarks_list else {}

    return "SUCCESS", face_crop, face_encoding, landmarks
