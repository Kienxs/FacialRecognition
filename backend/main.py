import json
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from database import get_db
import models
import security
from schemas import EnrollRequest, CheckInRequest
from ai_service.face_engine import process_face_pipeline
from ai_service.liveness import check_liveness
from fastapi.middleware.cors import CORSMiddleware
import numpy as np
import face_recognition

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
    # 1. Kiểm tra sinh viên có tồn tại trong hệ thống không, nếu chưa thì tự động tạo mới
    student = db.query(models.Student).filter(models.Student.mssv == req.mssv).first()
    if not student:
        student_name = req.name.strip() if req.name and req.name.strip() else f"Sinh viên {req.mssv}"
        student = models.Student(mssv=req.mssv, name=student_name)
        db.add(student)
        default_class = db.query(models.Class).filter(models.Class.id == "CS101").first()
        if default_class and student not in default_class.students:
            default_class.students.append(student)
        db.commit()
        db.refresh(student)

    # 2. Pipeline xử lý mặt & Quality Check
    status_code, face_crop, encoding_list, landmarks = process_face_pipeline(req.image_base64)
    if status_code == "NO_FACE":
        raise HTTPException(status_code=400, detail="Không tìm thấy khuôn mặt.")
    if status_code == "MULTIPLE_FACES":
        raise HTTPException(status_code=400, detail="Chỉ được phép có 1 khuôn mặt trong khung hình.")
        
    # 3. Kiểm tra chất lượng khuôn mặt lúc Enroll
    is_real, liveness_score, liveness_detail = check_liveness(face_crop)
    if liveness_score < 0.30 and not is_real:
        raise HTTPException(status_code=400, detail=f"Không thể đăng ký: {liveness_detail}. Vui lòng nhìn thẳng người thật vào camera.")

    # 4. Cập nhật Embedding mới (ghi đè embedding cũ của sinh viên này để lấy mẫu chuẩn nhất)
    db.query(models.FaceEmbedding).filter(models.FaceEmbedding.mssv == student.mssv).delete()
    new_embedding = models.FaceEmbedding(
        mssv=student.mssv,
        encoding_json=json.dumps(encoding_list),
        quality_score=float(liveness_score)
    )
    db.add(new_embedding)
    db.commit()
    
    return {"success": True, "message": f"Đã đăng ký thành công khuôn mặt cho {student.name}", "mssv": student.mssv}
 
@app.get("/")
def read_root():
    return {"message": "Facial Recognition Backend API is running"}

@app.get("/api/students")
def get_students(db: Session = Depends(get_db)):
    students = db.query(models.Student).all()
    return [
        {
            "mssv": s.mssv,
            "name": s.name,
            "enrolled": len(s.embeddings) > 0,
            "embeddings_count": len(s.embeddings)
        }
        for s in students
    ]

@app.delete("/api/students/{mssv}/face")
def delete_student_face(
    mssv: str,
    db: Session = Depends(get_db),
    current_teacher: models.Teacher = Depends(security.get_current_teacher)
):
    student = db.query(models.Student).filter(models.Student.mssv == mssv).first()
    if not student:
        raise HTTPException(status_code=404, detail="Không tìm thấy sinh viên.")
        
    deleted_count = db.query(models.FaceEmbedding).filter(models.FaceEmbedding.mssv == mssv).delete()
    db.commit()
    
    try:
        from ai_service.motion_liveness import reset_session
        reset_session(mssv)
    except Exception:
        pass
        
    return {
        "success": True, 
        "message": f"Đã xóa thành công khuôn mặt của sinh viên {student.name} ({mssv})",
        "deleted_count": deleted_count
    }

@app.post("/api/attendance/checkin")
def checkin(
    req: CheckInRequest, 
    db: Session = Depends(get_db),
    current_teacher: models.Teacher = Depends(security.get_current_teacher)
):
    # 1. Pipeline xử lý mặt & trích xuất landmarks
    status_code, face_crop, encoding_list, landmarks = process_face_pipeline(req.image_base64)
    if status_code != "SUCCESS" or encoding_list is None:
        return {"success": False, "status": "UNKNOWN", "detail": "Không phát hiện khuôn mặt hợp lệ"}

    # 2. Lớp 1: Kiểm tra dấu hiệu quang học Moiré & Phản quang chói lóa
    is_real_optical, liveness_score, liveness_detail = check_liveness(face_crop)
    if not is_real_optical:
        return {
            "success": False, 
            "status": "SPOOF_WARNING", 
            "detail": "Phát hiện hình ảnh không hợp lệ. Vui lòng nhìn trực tiếp vào camera."
        }

    # 3. So khớp khuôn mặt với cơ sở dữ liệu
    embeddings = db.query(models.FaceEmbedding).all()
    if not embeddings:
        return {"success": False, "status": "UNKNOWN", "detail": "Chưa có dữ liệu sinh viên đăng ký khuôn mặt"}

    known_encodings = [json.loads(e.encoding_json) for e in embeddings]
    distances = face_recognition.face_distance(known_encodings, np.array(encoding_list))
    min_dist_idx = int(np.argmin(distances))
    min_dist = float(distances[min_dist_idx])

    if min_dist > 0.55:
        return {"success": False, "status": "UNKNOWN", "detail": "Khuôn mặt chưa được nhận diện trong lớp"}

    matched_embedding = embeddings[min_dist_idx]
    student = db.query(models.Student).filter(models.Student.mssv == matched_embedding.mssv).first()
    if not student:
        return {"success": False, "status": "UNKNOWN", "detail": "Không tìm thấy hồ sơ sinh viên"}

    # 4. Lớp 2: Kiểm tra Động lực học Cử động sống (Blink & Micro-motion Dynamics)
    from ai_service.motion_liveness import evaluate_motion_liveness
    motion_status, motion_msg = evaluate_motion_liveness(student.mssv, landmarks)
    
    if motion_status == "CONFIRMED_SPOOF":
        # Ảnh tĩnh bất động 100% qua thời gian -> Chặn đứng gian lận!
        return {
            "success": False,
            "status": "SPOOF_WARNING",
            "detail": "Phát hiện hình ảnh không hợp lệ. Vui lòng nhìn trực tiếp vào camera."
        }
        
    if motion_status == "VERIFYING":
        # Đang phân tích chuỗi khung hình, yêu cầu giữ mặt tự nhiên
        return {
            "success": False,
            "status": "VERIFYING",
            "name": student.name,
            "mssv": student.mssv,
            "detail": "Đang xác thực cử động sống... Vui lòng nhìn tự nhiên trước camera."
        }

    # 4. Ghi nhận điểm danh
    today = models.get_vn_date()
    existing_record = db.query(models.AttendanceRecord).filter(
        models.AttendanceRecord.mssv == student.mssv,
        models.AttendanceRecord.class_id == req.class_id,
        models.AttendanceRecord.attendance_date == today
    ).first()

    if not existing_record:
        record = models.AttendanceRecord(
            mssv=student.mssv,
            class_id=req.class_id,
            attendance_date=today,
            status="SUCCESS",
            face_distance=min_dist,
            liveness_score=liveness_score
        )
        db.add(record)
        db.commit()

    return {
        "success": True,
        "mssv": student.mssv,
        "name": student.name,
        "face_distance": round(min_dist, 4)
    }