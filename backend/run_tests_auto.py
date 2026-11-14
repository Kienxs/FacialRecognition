import copy
import math
import numpy as np
import cv2
import face_recognition

from ai_service.liveness import check_liveness, analyze_spoof_features
from ai_service.motion_liveness import evaluate_motion_liveness, reset_session

def create_synthetic_face(has_moire=False, is_glare=False, is_flat_paper=False, r_boost=1.4):
    """Tạo khuôn mặt tổng hợp kiểm tra các đặc trưng vật lý và quang học"""
    img = np.ones((200, 200, 3), dtype=np.uint8) * 180
    # Da người: R trội hơn B
    img[:, :, 0] = np.clip(160 * r_boost, 0, 255) # Red
    img[:, :, 1] = 140                           # Green
    img[:, :, 2] = 120                           # Blue
    
    # Vẽ các đặc trưng: mắt, mũi, miệng
    cv2.circle(img, (70, 80), 12, (30, 20, 20), -1)  # Mắt trái
    cv2.circle(img, (130, 80), 12, (30, 20, 20), -1) # Mắt phải
    cv2.line(img, (100, 90), (100, 120), (50, 40, 40), 3) # Mũi
    cv2.ellipse(img, (100, 150), (25, 10), 0, 0, 180, (40, 30, 120), -1) # Miệng
    
    # 1. Thêm kết cấu da vi mô tự nhiên
    noise = np.random.normal(0, 8, img.shape).astype(np.float32)
    img = np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)
    
    if has_moire:
        # Lưới pixel màn hình LCD/OLED tần số cao (sọc 2D lặp)
        xx, yy = np.meshgrid(np.arange(200), np.arange(200))
        moire_pattern = (np.sin(xx * 0.8) * np.cos(yy * 0.8) * 28).astype(np.int16)
        img = np.clip(img.astype(np.int16) + moire_pattern[:, :, None], 0, 255).astype(np.uint8)
        
    if is_glare:
        # Vệt chói sáng lóa do phản quang kính điện thoại
        cv2.circle(img, (90, 90), 35, (255, 255, 255), -1)
        
    if is_flat_paper:
        # Ảnh giấy in mờ mất chi tiết da
        img = cv2.GaussianBlur(img, (11, 11), 0)
        
    return img

def get_base_landmarks():
    """Tạo bộ điểm mốc 68 điểm chuẩn cho một khuôn mặt"""
    img = np.zeros((300, 300, 3), dtype=np.uint8)
    # Lấy landmarks từ shape_predictor
    pts = face_recognition.face_landmarks(img, [(50, 250, 250, 50)])
    return pts[0]

def simulate_blink(landmarks, ear_scale=0.45):
    """Mô phỏng động tác chớp mắt bằng cách kéo mi trên xuống mi dưới"""
    lm = copy.deepcopy(landmarks)
    for eye_name in ['left_eye', 'right_eye']:
        eye = lm[eye_name]
        # p1: 0, p2: 1, p3: 2, p4: 3, p5: 4, p6: 5
        # Thu hẹp khoảng cách thẳng đứng p2-p6 và p3-p5
        mid_y1 = (eye[1][1] + eye[5][1]) / 2.0
        mid_y2 = (eye[2][1] + eye[4][1]) / 2.0
        eye[1] = (eye[1][0], int(eye[1][1] + (mid_y1 - eye[1][1]) * (1 - ear_scale)))
        eye[5] = (eye[5][0], int(eye[5][1] - (eye[5][1] - mid_y1) * (1 - ear_scale)))
        eye[2] = (eye[2][0], int(eye[2][1] + (mid_y2 - eye[2][1]) * (1 - ear_scale)))
        eye[4] = (eye[4][0], int(eye[4][1] - (eye[4][1] - mid_y2) * (1 - ear_scale)))
    return lm

def simulate_planar_rotation(landmarks, angle_deg=15, dx=10, dy=5):
    """Mô phỏng phép xoay/đổi góc điện thoại (Biến đổi affine 2D cứng của mặt phẳng)"""
    lm = copy.deepcopy(landmarks)
    rad = math.radians(angle_deg)
    cos_a, sin_a = math.cos(rad), math.sin(rad)
    cx, cy = 150.0, 150.0
    for part in lm:
        new_pts = []
        for (x, y) in lm[part]:
            nx = (x - cx) * cos_a - (y - cy) * sin_a + cx + dx
            ny = (x - cx) * sin_a + (y - cy) * cos_a + cy + dy
            new_pts.append((int(nx), int(ny)))
        lm[part] = new_pts
    return lm

def simulate_3d_facial_movement(landmarks):
    """Mô phỏng cử động cơ mặt 3D phi tuyến (mũi dịch chuyển parallax, miệng cười dãn)"""
    lm = copy.deepcopy(landmarks)
    # Mũi nhô cao dịch chuyển sang phải nhiều hơn
    lm['nose_tip'] = [(x + 9, y) for (x, y) in lm['nose_tip']]
    # Miệng dãn rộng do mỉm cười
    lm['top_lip'] = [(int(x * 1.06), y) for (x, y) in lm['top_lip']]
    lm['bottom_lip'] = [(int(x * 1.06), y) for (x, y) in lm['bottom_lip']]
    return lm

def run_all_tests():
    print("=" * 70)
    print("      BẮT ĐẦU CHẠY KIỂM THỬ TỰ ĐỘNG CÁC HẠNG MỤC TEST CASE")
    print("=" * 70)
    
    results = {}
    base_lm = get_base_landmarks()
    
    # ── TEST 1: TC-SEC-01 (Ảnh màn hình điện thoại - Moiré Lưới LCD) ──
    spoof_phone = create_synthetic_face(has_moire=True, r_boost=0.95)
    is_spoof, reasons, peak, glare, lap, rb = analyze_spoof_features(spoof_phone)
    passed_1 = is_spoof and any("Moiré" in r or "phát quang" in r for r in reasons)
    results["TC-SEC-01: Màn hình điện thoại (Moiré & LED Backlight)"] = {
        "status": "PASS" if passed_1 else "FAIL",
        "detail": f"Spoof={is_spoof}, Peak={peak:.2f}, R/B={rb:.2f}, Reasons={reasons}"
    }

    # ── TEST 2: TC-SEC-02 (Ảnh điện thoại đổi góc / nghiêng 2D) ──
    reset_session("TEST_SPOOF_ROTATE")
    status_history = []
    # Khung 1: Mặt ban đầu trên điện thoại
    s1, _ = evaluate_motion_liveness("TEST_SPOOF_ROTATE", base_lm)
    status_history.append(s1)
    # Khung 2 & 3: Xoay nghiêng điện thoại 12-25 độ
    lm_rot1 = simulate_planar_rotation(base_lm, angle_deg=10, dx=8, dy=4)
    s2, _ = evaluate_motion_liveness("TEST_SPOOF_ROTATE", lm_rot1)
    status_history.append(s2)
    
    import time
    time.sleep(1.3) # Giả lập thời gian trôi qua 1.3s
    lm_rot2 = simulate_planar_rotation(base_lm, angle_deg=20, dx=16, dy=8)
    s3, msg3 = evaluate_motion_liveness("TEST_SPOOF_ROTATE", lm_rot2)
    status_history.append(s3)
    
    passed_2 = (s3 == "CONFIRMED_SPOOF")
    results["TC-SEC-02: Ảnh điện thoại đổi góc (Planar 2D Residual Test)"] = {
        "status": "PASS" if passed_2 else "FAIL",
        "detail": f"Frames={status_history}, FinalStatus={s3}, Message={msg3}"
    }

    # ── TEST 3: TC-SEC-04 (Ảnh in phẳng giấy / Mặt kính phản quang) ──
    glare_face = create_synthetic_face(is_glare=True)
    is_spoof_g, reasons_g, _, glare_val, _, _ = analyze_spoof_features(glare_face)
    passed_3 = is_spoof_g and any("phản quang" in r for r in reasons_g)
    results["TC-SEC-04: Ảnh phản quang mặt kính / Ép bóng"] = {
        "status": "PASS" if passed_3 else "FAIL",
        "detail": f"Spoof={is_spoof_g}, GlareRatio={glare_val:.3f}, Reasons={reasons_g}"
    }

    # ── TEST 4: TC-LIVE-01 (Người thật chớp mắt tự nhiên) ──
    reset_session("TEST_LIVE_BLINK")
    # Khung 1: Mắt mở bình thường
    s_l1, _ = evaluate_motion_liveness("TEST_LIVE_BLINK", base_lm)
    # Khung 2: Nhắm mắt (chớp mắt)
    lm_blink = simulate_blink(base_lm, ear_scale=0.35)
    s_l2, msg_l2 = evaluate_motion_liveness("TEST_LIVE_BLINK", lm_blink)
    
    passed_4 = (s_l2 == "CONFIRMED_LIVE")
    results["TC-LIVE-01: Người thật chớp mắt (True Blink Detection)"] = {
        "status": "PASS" if passed_4 else "FAIL",
        "detail": f"Step1={s_l1}, Step2={s_l2}, Message={msg_l2}"
    }

    # ── TEST 5: TC-LIVE-02 (Người thật cử động biểu cảm 3D không chớp mắt) ──
    reset_session("TEST_LIVE_3D")
    s_3d1, _ = evaluate_motion_liveness("TEST_LIVE_3D", base_lm)
    lm_3d = simulate_3d_facial_movement(base_lm)
    s_3d2, msg_3d2 = evaluate_motion_liveness("TEST_LIVE_3D", lm_3d)
    passed_5 = (s_3d2 == "CONFIRMED_LIVE")
    results["TC-LIVE-02: Cử động biểu cảm 3D sống (3D Facial Parallax)"] = {
        "status": "PASS" if passed_5 else "FAIL",
        "detail": f"Step1={s_3d1}, Step2={s_3d2}, Message={msg_3d2}"
    }

    print("\n" + "=" * 70)
    print("                      KẾT QUẢ KIỂM THỬ TỪNG HẠNG MỤC")
    print("=" * 70)
    for tc, res in results.items():
        icon = "✅ [THÀNH CÔNG]" if res["status"] == "PASS" else "❌ [THẤT BÀI]"
        print(f"{icon} {tc}")
        print(f"      Chi tiết: {res['detail']}\n")
    print("=" * 70)

if __name__ == "__main__":
    run_all_tests()
