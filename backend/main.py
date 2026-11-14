# main.py
import json
from typing import Optional
from pydantic import BaseModel
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import numpy as np
import face_recognition

from database import get_db
import models
import security
from schemas import EnrollRequest, CheckInRequest
from ai_service.face_engine import process_face_pipeline
from ai_service.liveness import check_liveness
from ai_service.motion_liveness import evaluate_motion_liveness, reset_session

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ngưỡng khoảng cách Euclidean tối ưu cho khuôn mặt người Việt (dlib 128-d)
FACE_MATCH_THRESHOLD = 0.50
MAX_EMBEDDINGS_PER_STUDENT = 3

class TeacherLoginRequest(BaseModel):
    username: str
    password: str

@app.post("/api/auth/login")
def login_form(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    teacher = db.query(models.Teacher).filter(models.Teacher.id == form_data.username).first()
    if not teacher or not security.verify_password(form_data.password, teacher.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sai mã giảng viên hoặc mật khẩu",
        )
    access_token = security.create_access_token(data={"sub": teacher.id})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/teachers/login")
def login_json(req: TeacherLoginRequest, db: Session = Depends(get_db)):
    teacher = db.query(models.Teacher).filter(models.Teacher.id == req.username).first()
    if not teacher or not security.verify_password(req.password, teacher.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sai mã giảng viên hoặc mật khẩu",
        )
    access_token = security.create_access_token(data={"sub": teacher.id})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/classes")
def get_classes(
    db: Session = Depends(get_db),
    current_teacher: models.Teacher = Depends(security.get_current_teacher)
):
    classes = db.query(models.Class).filter(models.Class.teacher_id == current_teacher.id).all()
    if not classes:
        classes = db.query(models.Class).all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "teacher_id": c.teacher_id,
            "student_count": len(c.students)
        }
        for c in classes
    ]

@app.get("/api/classes/{class_id}/students")
def get_class_students(
    class_id: str,
    db: Session = Depends(get_db),
    current_teacher: models.Teacher = Depends(security.get_current_teacher)
):
    target_class = db.query(models.Class).filter(models.Class.id == class_id).first()
    if not target_class:
        raise HTTPException(status_code=404, detail="Không tìm thấy lớp học.")
    today = models.get_vn_date()
    attended_mssvs = {
        r.mssv for r in db.query(models.AttendanceRecord).filter(
            models.AttendanceRecord.class_id == class_id,
            models.AttendanceRecord.attendance_date == today,
            models.AttendanceRecord.status == "SUCCESS"
        ).all()
    }
    return [
        {
            "mssv": s.mssv,
            "name": s.name,
            "enrolled": len(s.embeddings) > 0,
            "embeddings_count": len(s.embeddings),
            "attended_today": s.mssv in attended_mssvs
        }
        for s in target_class.students
    ]

@app.post("/api/students/enroll")
def enroll_face(
    req: EnrollRequest,
    db: Session = Depends(get_db),
    current_teacher: models.Teacher = Depends(security.get_current_teacher)
):
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

    # Dùng num_jitters=2 khi đăng ký để trích xuất vector chuẩn xác hơn
    status_code, face_crop, encoding_list, landmarks = process_face_pipeline(req.image_base64, num_jitters=2)
    if status_code == "NO_FACE":
        raise HTTPException(status_code=400, detail="Không tìm thấy khuôn mặt.")
    if status_code == "MULTIPLE_FACES":
        raise HTTPException(status_code=400, detail="Chỉ được phép có 1 khuôn mặt trong khung hình.")

    is_real, liveness_score, liveness_detail = check_liveness(face_crop)
    if not is_real and liveness_score < 0.35:
        raise HTTPException(
            status_code=400,
            detail=f"Không thể đăng ký: {liveness_detail}. Vui lòng nhìn thẳng người thật vào camera."
        )

    # Lưu tối đa 3 mẫu khuôn mặt cho mỗi sinh viên (giữ các góc mặt đa dạng thay vì xóa sạch)
    existing_embeddings = (
        db.query(models.FaceEmbedding)
        .filter(models.FaceEmbedding.mssv == student.mssv)
        .order_by(models.FaceEmbedding.id.asc())
        .all()
    )
    if len(existing_embeddings) >= MAX_EMBEDDINGS_PER_STUDENT:
        db.delete(existing_embeddings[0])

    new_embedding = models.FaceEmbedding(
        mssv=student.mssv,
        encoding_json=json.dumps(encoding_list),
        quality_score=float(liveness_score)
    )
    db.add(new_embedding)
    db.commit()

    return {
        "success": True,
        "message": f"Đã đăng ký thành công khuôn mặt cho {student.name}",
        "mssv": student.mssv
    }

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
    reset_session(mssv)

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
    status_code, face_crop, encoding_list, landmarks = process_face_pipeline(req.image_base64, num_jitters=1)
    if status_code != "SUCCESS" or encoding_list is None:
        return {
            "success": False,
            "status": status_code,
            "detail": "Không phát hiện khuôn mặt hợp lệ"
        }

    # 2. Lớp 1: Kiểm tra dấu hiệu quang học & LivenessCNN
    is_real_optical, liveness_score, liveness_detail = check_liveness(face_crop)
    if not is_real_optical:
        return {
            "success": False,
            "status": "SPOOF_WARNING",
            "detail": f"Phát hiện hình ảnh không hợp lệ ({liveness_detail}). Vui lòng nhìn trực tiếp vào camera."
        }

    # 3. So khớp khuôn mặt với cơ sở dữ liệu
    embeddings = db.query(models.FaceEmbedding).all()
    if not embeddings:
        return {"success": False, "status": "UNKNOWN", "detail": "Chưa có dữ liệu sinh viên đăng ký khuôn mặt"}

    known_encodings = [json.loads(e.encoding_json) for e in embeddings]
    distances = face_recognition.face_distance(known_encodings, np.array(encoding_list))
    min_dist_idx = int(np.argmin(distances))
    min_dist = float(distances[min_dist_idx])

    if min_dist > FACE_MATCH_THRESHOLD:
        return {
            "success": False,
            "status": "UNKNOWN",
            "detail": "Khuôn mặt chưa được nhận diện trong lớp",
            "face_distance": round(min_dist, 4)
        }

    matched_embedding = embeddings[min_dist_idx]
    student = db.query(models.Student).filter(models.Student.mssv == matched_embedding.mssv).first()
    if not student:
        return {"success": False, "status": "UNKNOWN", "detail": "Không tìm thấy hồ sơ sinh viên"}

    # 4. Lớp 2: Kiểm tra Động lực học Cử động sống (Blink + 3D Parallax)
    motion_status, motion_msg = evaluate_motion_liveness(student.mssv, landmarks)

    if motion_status == "CONFIRMED_SPOOF":
        return {
            "success": False,
            "status": "SPOOF_WARNING",
            "detail": motion_msg
        }

    if motion_status == "VERIFYING":
        return {
            "success": False,
            "status": "VERIFYING",
            "name": student.name,
            "mssv": student.mssv,
            "detail": motion_msg
        }

    # 5. Ghi nhận điểm danh
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
        "status": "SUCCESS",
        "mssv": student.mssv,
        "name": student.name,
        "face_distance": round(min_dist, 4)
    }
