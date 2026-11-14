from database import SessionLocal
import models
from security import get_password_hash

def seed_data():
    db = SessionLocal()
    
    try:
        # 1. Kiểm tra xem tài khoản GV001 đã tồn tại chưa
        teacher = db.query(models.Teacher).filter(models.Teacher.id == "GV001").first()
        
        if not teacher:
            print("Đang tạo tài khoản Giảng viên...")
            # Mã hóa mật khẩu trước khi lưu
            hashed_pw = get_password_hash("123456")
            new_teacher = models.Teacher(
                id="GV001", 
                name="Nguyễn Văn An", 
                password_hash=hashed_pw
            )
            db.add(new_teacher)
            
            print("Đang tạo lớp học mẫu...")
            # Tạo 1 lớp học thuộc về giảng viên này để test Dashboard
            new_class = models.Class(
                id="CS101", 
                name="Nhập môn CNTT", 
                teacher_id="GV001"
            )
            db.add(new_class)
            
            db.commit()
            print("✅ Khởi tạo thành công!")
            print("👉 Tên đăng nhập: GV001")
            print("👉 Mật khẩu: 123456")
        else:
            print("Tài khoản GV001 đã tồn tại. Bạn có thể dùng luôn.")

        # 2. Tạo sinh viên mẫu nếu chưa có
        sample_students = [
            {"mssv": "20210001", "name": "Lê Minh Tuấn"},
            {"mssv": "20210015", "name": "Nguyễn Thị Hoa"},
            {"mssv": "20210023", "name": "Trần Đức Anh"},
            {"mssv": "20210037", "name": "Phạm Thanh Hằng"},
            {"mssv": "20210042", "name": "Vũ Hoàng Long"},
            {"mssv": "20210056", "name": "Đỗ Thị Mai"},
            {"mssv": "20210064", "name": "Hoàng Văn Sơn"},
            {"mssv": "20210078", "name": "Bùi Ngọc Linh"},
        ]
        
        target_class = db.query(models.Class).filter(models.Class.id == "CS101").first()
        for s_data in sample_students:
            existing = db.query(models.Student).filter(models.Student.mssv == s_data["mssv"]).first()
            if not existing:
                student = models.Student(mssv=s_data["mssv"], name=s_data["name"])
                db.add(student)
                if target_class and student not in target_class.students:
                    target_class.students.append(student)
        
        db.commit()
        print("✅ Đã cập nhật danh sách sinh viên mẫu!")
            
    except Exception as e:
        print(f"Có lỗi xảy ra: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()