from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
# Import cấu trúc bảng từ models.py
from models import Base

# Chỉ định đường dẫn lưu file database (sẽ tự động tạo file attendance.db trong thư mục backend)
SQLALCHEMY_DATABASE_URL = "sqlite:///./attendance.db"

# Khởi tạo Engine (connect_args là bắt buộc cho SQLite khi dùng FastAPI)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Khởi tạo Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Lệnh này sẽ quét models.py và tự động tạo các bảng nếu chưa tồn tại
Base.metadata.create_all(bind=engine)

# Hàm Dependency dùng để mở/đóng kết nối CSDL an toàn cho mỗi request (API)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()