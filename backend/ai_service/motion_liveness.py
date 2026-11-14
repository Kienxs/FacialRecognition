# ai_service/motion_liveness.py
import time
import numpy as np

# Cấu trúc cache: { mssv: { 'start_time': float, 'last_seen': float, 'history': [ (all_pts, ear, timestamp) ] } }
_SESSION_CACHE = {}

def compute_ear(eye_points):
    """Tính Eye Aspect Ratio (EAR) từ 6 điểm mắt"""
    if len(eye_points) < 6:
        return 0.3
    p1, p2, p3, p4, p5, p6 = eye_points[:6]
    v1 = np.linalg.norm(np.array(p2, dtype=np.float32) - np.array(p6, dtype=np.float32))
    v2 = np.linalg.norm(np.array(p3, dtype=np.float32) - np.array(p5, dtype=np.float32))
    h = np.linalg.norm(np.array(p1, dtype=np.float32) - np.array(p4, dtype=np.float32))
    if h < 1e-5:
        return 0.3
    return float((v1 + v2) / (2.0 * h))

def extract_flat_points(landmarks):
    """Gộp toàn bộ 68 điểm mốc thành mảng NumPy (N, 2) và tính EAR trung bình 2 mắt"""
    try:
        all_pts = []
        ordered_features = [
            'chin', 'left_eyebrow', 'right_eyebrow',
            'nose_bridge', 'nose_tip', 'left_eye',
            'right_eye', 'top_lip', 'bottom_lip'
        ]
        for feature in ordered_features:
            if feature in landmarks:
                all_pts.extend(landmarks[feature])

        if len(all_pts) < 50:
            return None, 0.3

        all_pts = np.array(all_pts, dtype=np.float32)

        left_eye = landmarks.get('left_eye', [])
        right_eye = landmarks.get('right_eye', [])
        if left_eye and right_eye:
            left_ear = compute_ear(left_eye)
            right_ear = compute_ear(right_eye)
            avg_ear = (left_ear + right_ear) / 2.0
        else:
            avg_ear = 0.3

        return all_pts, float(avg_ear)
    except Exception:
        return None, 0.3

def compute_non_rigid_residual(pts_ref: np.ndarray, pts_cur: np.ndarray) -> float:
    """
    Tính sai số biến dạng 3D phi tuyến (Non-Rigid / 3D Parallax Residual):
    - Khớp phép biến đổi phẳng 2D Affine: pts_cur ≈ [pts_ref, 1] @ M
    - Ảnh trên điện thoại xoay/nghiêng/dịch chuyển là mặt phẳng 2D cứng -> Residual rất nhỏ (< 0.85 px).
    - Khuôn mặt 3D thật cử động cơ mặt hoặc xoay đầu có độ nhô chóp mũi & biến dạng môi -> Residual lớn (>= 1.20 px).
    """
    if pts_ref.shape != pts_cur.shape or len(pts_ref) < 50:
        return 0.0
    ones = np.ones((pts_ref.shape[0], 1), dtype=np.float32)
    A = np.hstack([pts_ref, ones])
    M, _, _, _ = np.linalg.lstsq(A, pts_cur, rcond=None)
    projected = A @ M
    errors = np.linalg.norm(pts_cur - projected, axis=1)
    return float(np.mean(errors))

def evaluate_motion_liveness(mssv: str, landmarks):
    """
    Kiểm định Sinh trắc học Động lực học Kép (Chớp mắt tự nhiên + Biến dạng 3D Parallax):
    1. Chấp nhận CONFIRMED_LIVE khi:
       - Phát hiện chu kỳ chớp mắt thật (EAR biến thiên >= 0.038 và giảm >= 15% so với mức mở mắt).
       - Hoặc phát hiện cử động biểu cảm/thị sai 3D thực thụ (Non-rigid residual >= 1.20 px).
    2. Chặn CONFIRMED_SPOOF khi:
       - Điện thoại xoay/nghiêng phẳng 2D (Dịch chuyển lớn nhưng sai số phẳng 2D < 0.85 px và không chớp mắt sau >= 1.2s).
       - Hoặc ảnh tĩnh hoàn toàn không có chớp mắt/biến dạng 3D sau thời gian theo dõi.
    """
    now = time.time()

    # Dọn dẹp cache các phiên cũ quá 8 giây
    expired_keys = [k for k, v in _SESSION_CACHE.items() if now - v['last_seen'] > 8.0]
    for k in expired_keys:
        del _SESSION_CACHE[k]

    pts, ear = extract_flat_points(landmarks)
    if pts is None:
        return "VERIFYING", "Đang căn chỉnh khuôn mặt..."

    if mssv not in _SESSION_CACHE:
        _SESSION_CACHE[mssv] = {
            'start_time': now,
            'last_seen': now,
            'history': [(pts, ear, now)]
        }
        return "VERIFYING", "Vui lòng nhìn tự nhiên và chớp mắt trước camera..."

    session = _SESSION_CACHE[mssv]
    session['last_seen'] = now
    history = session['history']
    history.append((pts, ear, now))

    if len(history) > 12:
        history.pop(0)

    ears = [h[1] for h in history]
    min_ear = min(ears)
    max_ear = max(ears)
    ear_range = max_ear - min_ear
    ear_drop_ratio = ear_range / (max_ear + 1e-5)
    elapsed = now - session['start_time']

    pts_first = history[0][0]
    pts_prev = history[-2][0]
    pts_curr = history[-1][0]

    step_displacement = float(np.mean(np.linalg.norm(pts_curr - pts_prev, axis=1)))
    total_displacement = float(np.mean(np.linalg.norm(pts_curr - pts_first, axis=1)))

    # Tính sai số biến dạng 3D lớn nhất giữa frame đầu và các frame tiếp theo
    max_residual = max(compute_non_rigid_residual(pts_first, h[0]) for h in history[1:])

    print(
        f"[MOTION LIVENESS] MSSV: {mssv} | Frames: {len(history)} | EAR: {ear:.3f} "
        f"| Range: {ear_range:.3f} (Drop: {ear_drop_ratio*100:.1f}%) "
        f"| 3D-Residual: {max_residual:.2f}px | Move: {total_displacement:.1f}px | Time: {elapsed:.1f}s"
    )

    # ── TRƯỜNG HỢP 1: PHÁT HIỆN CHỚP MẮT THẬT ──
    if (ear_range >= 0.038 and min_ear < 0.245) or (ear_range >= 0.035 and ear_drop_ratio >= 0.15):
        del _SESSION_CACHE[mssv]
        print(f"[MOTION LIVENESS] >> BLINK CONFIRMED! Range: {ear_range:.3f} -> CONFIRMED LIVE")
        return "CONFIRMED_LIVE", "Xác nhận người thật (Chớp mắt tự nhiên)"

    # ── TRƯỜNG HỢP 2: PHÁT HIỆN CỬ ĐỘNG CƠ MẶT / THỊ SAI 3D THẬT (KHÔNG PHẢI XOAY PHẲNG 2D) ──
    if max_residual >= 1.20 and total_displacement < 45.0:
        del _SESSION_CACHE[mssv]
        print(f"[MOTION LIVENESS] >> 3D PARALLAX CONFIRMED! Residual: {max_residual:.2f}px -> CONFIRMED LIVE")
        return "CONFIRMED_LIVE", "Xác nhận người thật (Cử động biểu cảm 3D tự nhiên)"

    # ── TRƯỜNG HỢP 3: PHÁT HIỆN GIAN LẬN XOAY/NGHIÊNG ĐIỆN THOẠI PHẲNG 2D ──
    # Có dịch chuyển lớn (>= 4px) nhưng toàn bộ điểm mốc biến đổi cứng trên mặt phẳng 2D (max_residual < 0.85px)
    if len(history) >= 3 and elapsed >= 1.2 and total_displacement >= 4.0 and max_residual < 0.85 and ear_range < 0.025:
        del _SESSION_CACHE[mssv]
        print(f"[MOTION LIVENESS] >> 2D PLANAR SPOOF DETECTED! Move={total_displacement:.1f}px, Residual={max_residual:.2f}px -> CONFIRMED SPOOF")
        return "CONFIRMED_SPOOF", "Phát hiện hình ảnh phẳng 2D đổi góc (Không có cấu trúc 3D và chớp mắt)."

    # ── TRƯỜNG HỢP 4: ẢNH TĨNH BẤT ĐỘNG HOÀN TOÀN QUA THỜI GIAN ──
    if len(history) >= 5 and elapsed >= 2.8:
        del _SESSION_CACHE[mssv]
        print(f"[MOTION LIVENESS] >> STATIC SPOOF DETECTED over {elapsed:.1f}s -> CONFIRMED SPOOF")
        return "CONFIRMED_SPOOF", "Phát hiện hình ảnh tĩnh không hợp lệ (Không có cử động sống)."

    return "VERIFYING", "Vui lòng nhìn tự nhiên và chớp mắt trước camera..."

def reset_session(mssv: str):
    """Xóa cache của một sinh viên nếu cần"""
    if mssv in _SESSION_CACHE:
        del _SESSION_CACHE[mssv]