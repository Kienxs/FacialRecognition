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
            
    except Exception as e:
        print(f"Có lỗi xảy ra: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()