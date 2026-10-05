import json
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from database import get_db
import models
import security
from schemas import EnrollRequest
from ai_service.face_engine import process_face_pipeline
from ai_service.liveness import check_liveness
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Trong thực tế nên đổi thành ["http://localhost:5173"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Bắt lỗi Liveness Model chưa load ngay từ lúc khởi động server
try:
    # Trigger load model inside liveness.py
    import ai_service.liveness 
except Exception as e:
    raise RuntimeError(f"CRITICAL: Không thể khởi tạo Liveness Model. Chi tiết: {str(e)}")

@app.post("/api/auth/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    teacher = db.query(models.Teacher).filter(models.Teacher.id == form_data.username).first()
    if not teacher or not security.verify_password(form_data.password, teacher.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sai mã giảng viên hoặc mật khẩu",
        )
    access_token = security.create_access_token(data={"sub": teacher.id})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/students/enroll")
def enroll_face(
    req: EnrollRequest, 
    db: Session = Depends(get_db),
    current_teacher: models.Teacher = Depends(security.get_current_teacher) # BẢO MẬT: Bắt buộc Auth
):
    # 1. Kiểm tra sinh viên có tồn tại trong hệ thống không
    student = db.query(models.Student).filter(models.Student.mssv == req.mssv).first()
    if not student:
        raise HTTPException(status_code=404, detail="Sinh viên không tồn tại trong hệ thống. Vui lòng nhập DB trước.")

    # 2. Pipeline xử lý mặt & Quality Check
    status_code, face_crop, encoding_list = process_face_pipeline(req.image_base64)
    if status_code == "NO_FACE":
        raise HTTPException(status_code=400, detail="Không tìm thấy khuôn mặt.")
    if status_code == "MULTIPLE_FACES":
        raise HTTPException(status_code=400, detail="Chỉ được phép có 1 khuôn mặt trong khung hình.")
        
    # (Tương lai: Thêm Face Quality Check tại đây)

    # 3. Liveness Check
    is_real, liveness_score = check_liveness(face_crop)
    if not is_real:
        raise HTTPException(status_code=400, detail=f"Phát hiện gian lận. Liveness score: {liveness_score:.2f}")

    # 4. Lưu Embedding mới thành bản ghi riêng (Không ghi đè)
    new_embedding = models.FaceEmbedding(
        mssv=student.mssv,
        encoding_json=json.dumps(encoding_list),
        quality_score=0.95 # Giá trị placeholder, thay bằng hàm quality check thực tế
    )
    db.add(new_embedding)
    db.commit()
    
    return {"success": True, "message": f"Đã thêm vector khuôn mặt mới cho {student.name}"}