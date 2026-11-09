import time
import numpy as np
import cv2

# Bộ nhớ đệm lưu vết trạng thái của từng sinh viên đang đứng trước camera
# Cấu trúc: { mssv: { 'start_time': float, 'last_seen': float, 'history': [ (all_pts, ear, timestamp) ] } }
_SESSION_CACHE = {}

def compute_ear(eye_points):
    """Tính Eye Aspect Ratio (EAR) từ 6 điểm mắt"""
    if len(eye_points) < 6:
        return 0.3
    p1, p2, p3, p4, p5, p6 = eye_points[:6]
    v1 = np.linalg.norm(np.array(p2) - np.array(p6))
    v2 = np.linalg.norm(np.array(p3) - np.array(p5))
    h = np.linalg.norm(np.array(p1) - np.array(p4))
    if h < 1e-5:
        return 0.3
    return float((v1 + v2) / (2.0 * h))

def extract_flat_points(landmarks):
    """
    Gộp toàn bộ 68 điểm mốc thành mảng NumPy (N, 2) và tính EAR trung bình 2 mắt
    """
    try:
        all_pts = []
        for feature in ['chin', 'left_eyebrow', 'right_eyebrow', 'nose_bridge', 'nose_tip', 'left_eye', 'right_eye', 'top_lip', 'bottom_lip']:
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
    except Exception as e:
        return None, 0.3

def evaluate_motion_liveness(mssv: str, landmarks):
    """
    KIỂM ĐỊNH SINH TRẮC HỌC BẮT BUỘC CHỚP MẮT (MANDATORY BLINK LIVENESS):
    
    NGUYÊN TẮC BẢO MẬT TUYỆT ĐỐI:
    - Bất kỳ bức ảnh tĩnh nào trên điện thoại (dù để thẳng, nghiêng góc nhỏ, đổi góc lớn,
      lắc lư, zoom to/nhỏ hay xoay vòng) đều KHÔNG THỂ CHỚP MẮT THẬT SỰ.
    - Người thật đứng trước camera luôn chớp mắt tự nhiên theo chu kỳ sinh học (1-3 giây/lần).
    - Vì vậy, CHỈ CÔNG NHẬN LÀ NGƯỜI THẬT khi phát hiện một chu kỳ chớp mắt thực thụ:
      Độ mở mắt EAR có sự sụt giảm và hồi phục với biên độ rõ rệt (ear_range >= 0.040).
      
    - Mọi trường hợp mặt cử động/nghiêng/xoay mà KHÔNG CÓ CHỚP MẮT:
      Hệ thống giữ trạng thái VERIFYING (yêu cầu chớp mắt).
      Nếu sau 2.0 giây mà vẫn hoàn toàn không chớp mắt -> CHẶN ĐỨNG GIAN LẬN (CONFIRMED_SPOOF).
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
        return "VERIFYING", "Vui lòng chớp mắt tự nhiên trước camera..."
        
    session = _SESSION_CACHE[mssv]
    session['last_seen'] = now
    history = session['history']
    history.append((pts, ear, now))
    
    # Giữ tối đa 10 frame gần nhất (~ 2 - 3 giây)
    if len(history) > 10:
        history.pop(0)
        
    ears = [h[1] for h in history]
    min_ear = min(ears)
    max_ear = max(ears)
    ear_range = max_ear - min_ear
    elapsed = now - session['start_time']
    
    # Đo chuyển động vị trí giữa 2 frame liên tiếp
    displacement = float(np.mean(np.linalg.norm(history[-1][0] - history[-2][0], axis=1)))
    
    print(f"[MOTION LIVENESS] MSSV: {mssv} | Frames: {len(history)} | EAR: {ear:.3f} | Range: {ear_range:.3f} (min={min_ear:.3f}, max={max_ear:.3f}) | Move: {displacement:.1f}px | Time: {elapsed:.1f}s")
    
    # ── ĐIỀU KIỆN TIÊN QUYẾT DUY NHẤT ĐỂ DUYỆT ĐIỂM DANH: CHỚP MẮT TỰ NHIÊN ──
    # Mắt mở bình thường: EAR ~ 0.26 - 0.35. Khi chớp mắt nhắm lại: EAR < 0.20 -> ear_range >= 0.040
    if ear_range >= 0.040 and min_ear < 0.24:
        del _SESSION_CACHE[mssv]
        print(f"[MOTION LIVENESS] >> BLINK CONFIRMED! Range: {ear_range:.3f} (min={min_ear:.3f}) -> CONFIRMED LIVE")
        return "CONFIRMED_LIVE", "Xác nhận người thật (Chớp mắt tự nhiên)"
        
    # ── PHÁT HIỆN GIAN LẬN: ẢNH TĨNH / ĐIỆN THOẠI ĐỔI GÓC KHÔNG THỂ CHỚP MẮT ──
    # Nếu đã theo dõi từ 4 frame trở lên HOẶC thời gian >= 1.8 giây mà hoàn toàn không chớp mắt (ear_range < 0.025)
    if (len(history) >= 3 and elapsed >= 1.2) or elapsed >= 1.8:
        del _SESSION_CACHE[mssv]
        print(f"[MOTION LIVENESS] >> SPOOF DETECTED: No True Blink over {elapsed:.1f}s (Range={ear_range:.3f}) -> CONFIRMED SPOOF")
        return "CONFIRMED_SPOOF", "Phát hiện hình ảnh không hợp lệ (Không có cử động chớp mắt)."
        
    # Đang tiếp tục theo dõi cử động chớp mắt
    return "VERIFYING", "Vui lòng chớp mắt tự nhiên trước camera..."

def reset_session(mssv: str):
    """Xóa cache của một sinh viên nếu cần"""
    if mssv in _SESSION_CACHE:
        del _SESSION_CACHE[mssv]
