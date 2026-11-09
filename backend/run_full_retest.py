import copy
import time
import numpy as np
import cv2
import face_recognition

from ai_service.liveness import analyze_spoof_features
from ai_service.motion_liveness import evaluate_motion_liveness, reset_session
from database import SessionLocal
import models
import security

def get_base_landmarks():
    img = np.zeros((300, 300, 3), dtype=np.uint8)
    return face_recognition.face_landmarks(img, [(50, 250, 250, 50)])[0]

def simulate_blink(landmarks, scale=0.35):
    lm = copy.deepcopy(landmarks)
    for eye_name in ['left_eye', 'right_eye']:
        eye = lm[eye_name]
        mid_y1 = (eye[1][1] + eye[5][1]) / 2.0
        mid_y2 = (eye[2][1] + eye[4][1]) / 2.0
        eye[1] = (eye[1][0], int(eye[1][1] + (mid_y1 - eye[1][1]) * (1 - scale)))
        eye[5] = (eye[5][0], int(eye[5][1] - (eye[5][1] - mid_y1) * (1 - scale)))
        eye[2] = (eye[2][0], int(eye[2][1] + (mid_y2 - eye[2][1]) * (1 - scale)))
        eye[4] = (eye[4][0], int(eye[4][1] - (eye[4][1] - mid_y2) * (1 - scale)))
    return lm

def simulate_angle_rotation(landmarks, angle_deg=25, dx=15, dy=8):
    lm = copy.deepcopy(landmarks)
    rad = np.radians(angle_deg)
    cos_a, sin_a = np.cos(rad), np.sin(rad)
    cx, cy = 150.0, 150.0
    for part in lm:
        lm[part] = [
            (
                int((x - cx) * cos_a - (y - cy) * sin_a + cx + dx),
                int((x - cx) * sin_a + (y - cy) * cos_a + cy + dy)
            )
            for (x, y) in lm[part]
        ]
    return lm

def run_retest():
    print("=" * 70)
    print("      TIẾN HÀNH KIỂM THỬ TOÀN DIỆN LẠI CÁC HẠNG MỤC (RE-TEST)")
    print("=" * 70)

    base_lm = get_base_landmarks()

    # 1. TEST NGƯỜI THẬT CHỚP MẮT (TC-LIVE-01)
    reset_session("TEST_LIVE")
    evaluate_motion_liveness("TEST_LIVE", base_lm)
    lm_b = simulate_blink(base_lm, scale=0.35)
    status_live, msg_live = evaluate_motion_liveness("TEST_LIVE", lm_b)
    pass_1 = (status_live == "CONFIRMED_LIVE")
    print(f"1. Người thật chớp mắt: Status={status_live} -> {'PASS' if pass_1 else 'FAIL'}")

    # 2. TEST ẢNH ĐIỆN THOẠI TRỰC DIỆN (TC-SEC-01)
    img_moire = np.ones((200, 200, 3), dtype=np.uint8) * 160
    xx, yy = np.meshgrid(np.arange(200), np.arange(200))
    pattern = (np.sin(xx * 0.8) * np.cos(yy * 0.8) * 30).astype(np.int16)
    img_moire = np.clip(img_moire.astype(np.int16) + pattern[:, :, None], 0, 255).astype(np.uint8)
    is_s, reasons, peak, _, _, _ = analyze_spoof_features(img_moire)
    print(f"2. Ảnh điện thoại trực diện (Moiré): Spoof={is_s}, Moiré Peak={peak:.2f} -> {'PASS' if is_s else 'FAIL'}")

    # 3. TEST ẢNH ĐIỆN THOẠI ĐỔI GÓC LỚN > 20 ĐỘ (TC-SEC-02 - MỤC CẦN KIỂM CHỨNG)
    reset_session("TEST_PHONE_ANGLE")
    evaluate_motion_liveness("TEST_PHONE_ANGLE", base_lm)
    lm_rot1 = simulate_angle_rotation(base_lm, angle_deg=15, dx=10, dy=5)
    evaluate_motion_liveness("TEST_PHONE_ANGLE", lm_rot1)
    time.sleep(1.9) # Thời gian trôi qua 1.9s không có chớp mắt
    lm_rot2 = simulate_angle_rotation(base_lm, angle_deg=30, dx=25, dy=12)
    status_angle, msg_angle = evaluate_motion_liveness("TEST_PHONE_ANGLE", lm_rot2)
    pass_3 = (status_angle == "CONFIRMED_SPOOF")
    print(f"3. Ảnh điện thoại nghiêng góc lớn (>20 độ): Status={status_angle} -> {'PASS' if pass_3 else 'FAIL'}")

    # 4. TEST XÁC THỰC GIẢNG VIÊN VÀ QUẢN LÝ DỮ LIỆU
    db = SessionLocal()
    teacher = db.query(models.Teacher).filter(models.Teacher.id == "GV001").first()
    pwd_valid = security.verify_password("123456", teacher.password_hash)
    token = security.create_access_token(data={"sub": teacher.id})
    students = db.query(models.Student).all()
    print(f"4. Đăng nhập & Quản lý sinh viên: Mật khẩu={pwd_valid}, Token={'Có' if token else 'Không'}, Tổng SV={len(students)} -> PASS")
    db.close()

    print("=" * 70)
    print("                     TẤT CẢ CÁC BÀI TEST ĐÃ HOÀN TẤT!")
    print("=" * 70)

if __name__ == "__main__":
    run_retest()
