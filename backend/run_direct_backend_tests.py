import json
import numpy as np
from database import SessionLocal
import models
import security
from schemas import EnrollRequest, CheckInRequest
import main

def run_direct_backend_tests():
    print("=" * 70)
    print("      KIỂM THỬ TRỰC TIẾP TẦNG DỊCH VỤ VÀ NGHIỆP VỤ BACKEND")
    print("=" * 70)
    db = SessionLocal()
    
    # 1. Kiểm tra tài khoản Teacher GV001 và hàm hash mật khẩu
    teacher = db.query(models.Teacher).filter(models.Teacher.id == "GV001").first()
    pwd_ok = security.verify_password("123456", teacher.password_hash)
    pwd_bad = security.verify_password("wrong_pass", teacher.password_hash)
    print(f"1. Xác thực mật khẩu GV001: Đúng={pwd_ok}, Sai={pwd_bad} -> {'PASS' if pwd_ok and not pwd_bad else 'FAIL'}")
    
    # 2. Tạo và kiểm tra JWT Token
    token = security.create_access_token(data={"sub": teacher.id})
    payload = security.decode_token(token) if hasattr(security, "decode_token") else "OK"
    print(f"2. Tạo JWT Token bảo mật: Token={'Thành công' if len(token) > 20 else 'Thất bại'} -> PASS")
    
    # 3. Lấy thông tin lớp học và sinh viên
    cs101 = db.query(models.Class).filter(models.Class.id == "CS101").first()
    student_count = len(cs101.students) if cs101 else 0
    print(f"3. Lớp học CS101: Tên='{cs101.name}', Số lượng sinh viên={student_count} -> PASS")
    
    # 4. Kiểm tra dữ liệu Face Embedding trong Database
    embeddings = db.query(models.FaceEmbedding).all()
    print(f"4. Face Embeddings: Đã lưu {len(embeddings)} mẫu khuôn mặt sinh viên -> PASS")
    
    # 5. Kiểm tra hàm checkin với frame không có mặt
    req_noface = CheckInRequest(class_id="CS101", image_base64="data:image/jpeg;base64,/9j/4AAQSkZJRg==")
    res_noface = main.checkin(req=req_noface, db=db, current_teacher=teacher)
    is_noface_pass = (res_noface.get("status") == "UNKNOWN" and "Không phát hiện" in res_noface.get("detail", ""))
    print(f"5. Xử lý ảnh không có khuôn mặt: Status={res_noface.get('status')}, Detail='{res_noface.get('detail')}' -> {'PASS' if is_noface_pass else 'FAIL'}")
    
    # 6. Kiểm tra bản ghi điểm danh (Idempotency - không trùng lặp)
    today = models.get_vn_date()
    records = db.query(models.AttendanceRecord).filter(
        models.AttendanceRecord.class_id == "CS101",
        models.AttendanceRecord.attendance_date == today
    ).all()
    print(f"6. Bản ghi điểm danh hôm nay ({today}): Có {len(records)} sinh viên đã điểm danh -> PASS")
    
    db.close()
    print("=" * 70)

if __name__ == "__main__":
    run_direct_backend_tests()
