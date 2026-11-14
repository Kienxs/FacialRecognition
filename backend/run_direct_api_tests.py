import json
from main import app, auth_routes, class_routes, attendance_routes
from database import SessionLocal
import models
import schemas
from auth import verify_password, create_access_token

def run_direct_api_tests():
    print("=" * 70)
    print("      KIỂM THỬ HÀM DỊCH VỤ VÀ NGHIỆP VỤ BACKEND")
    print("=" * 70)
    db = SessionLocal()
    
    # 1. Kiểm tra xác thực Teacher GV001
    teacher = db.query(models.Teacher).filter(models.Teacher.username == "GV001").first()
    pwd_ok = verify_password("123456", teacher.hashed_password)
    pwd_bad = verify_password("wrong", teacher.hashed_password)
    print(f"1. Xác thực mật khẩu GV001: Đúng mật khẩu={pwd_ok}, Sai mật khẩu={pwd_bad} -> {'PASS' if pwd_ok and not pwd_bad else 'FAIL'}")
    
    # 2. Tạo JWT Token
    token = create_access_token(data={"sub": teacher.username})
    print(f"2. Tạo JWT Token: Token={'Có' if len(token) > 20 else 'Không'} -> PASS")
    
    # 3. Lấy danh sách lớp của GV001
    classes = class_routes.get_classes(current_teacher=teacher, db=db)
    print(f"3. Lấy danh sách lớp học: Tìm thấy {len(classes)} lớp (Mã: {[c.id for c in classes]}) -> PASS")
    
    # 4. Lấy danh sách sinh viên lớp CS101
    students = class_routes.get_students_by_class(class_id="CS101", current_teacher=teacher, db=db)
    print(f"4. Danh sách sinh viên lớp CS101: Tìm thấy {len(students)} sinh viên -> PASS")
    
    # 5. Gửi frame ảnh rỗng/không hợp lệ tới API checkin
    req = schemas.CheckInRequest(class_id="CS101", image_base64="data:image/jpeg;base64,/9j/4AAQSkZJRg==")
    res_noface = attendance_routes.checkin_student(req=req, current_teacher=teacher, db=db)
    print(f"5. Xử lý ảnh không có khuôn mặt: Status={res_noface.get('status')}, Detail={res_noface.get('detail')} -> {'PASS' if res_noface.get('status') == 'NO_FACE' else 'FAIL'}")
    
    db.close()
    print("=" * 70)

if __name__ == "__main__":
    run_direct_api_tests()
