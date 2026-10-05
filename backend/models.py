import pytz
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Date, Float, ForeignKey, UniqueConstraint, Table
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

def get_utc_now():
    return datetime.now(timezone.utc)

def get_vn_date():
    vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    return datetime.now(vn_tz).date()

# Bảng trung gian Nhiều-Nhiều giữa Student và Class
class_student_association = Table(
    'class_students', Base.metadata,
    Column('class_id', String, ForeignKey('classes.id'), primary_key=True),
    Column('mssv', String, ForeignKey('students.mssv'), primary_key=True)
)

class Teacher(Base):
    __tablename__ = "teachers"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    
    classes = relationship("Class", back_populates="teacher")

class Class(Base):
    __tablename__ = "classes"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    teacher_id = Column(String, ForeignKey("teachers.id"))
    
    teacher = relationship("Teacher", back_populates="classes")
    students = relationship("Student", secondary=class_student_association, back_populates="classes")

class Student(Base):
    __tablename__ = "students"
    mssv = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    
    classes = relationship("Class", secondary=class_student_association, back_populates="students")
    embeddings = relationship("FaceEmbedding", back_populates="student", cascade="all, delete-orphan")

# Lưu nhiều vector khuôn mặt cho 1 sinh viên (chính diện, nghiêng, thiếu sáng...)
class FaceEmbedding(Base):
    __tablename__ = "face_embeddings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    mssv = Column(String, ForeignKey("students.mssv"))
    encoding_json = Column(String, nullable=False) # Lưu vector 128 chiều
    quality_score = Column(Float, nullable=True)   # Điểm chất lượng ảnh lúc enroll
    
    student = relationship("Student", back_populates="embeddings")

class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    id = Column(Integer, primary_key=True, autoincrement=True)
    mssv = Column(String, ForeignKey("students.mssv"), nullable=False)
    class_id = Column(String, ForeignKey("classes.id"), nullable=False)
    
    # Tách biệt Date (để check unique) và Timestamp (để ghi log chính xác)
    attendance_date = Column(Date, default=get_vn_date, nullable=False)
    timestamp = Column(DateTime, default=get_utc_now, nullable=False)
    
    # Metadata chứng minh tính minh bạch
    status = Column(String, nullable=False) # SUCCESS, SPOOF_DETECTED, LOW_QUALITY...
    face_distance = Column(Float, nullable=True)
    liveness_score = Column(Float, nullable=True)
    spoof_type = Column(String, nullable=True)
    
    # Chặn Race Condition và Spam điểm danh
    __table_args__ = (
        UniqueConstraint('mssv', 'class_id', 'attendance_date', name='uq_attendance_per_day'),
    )