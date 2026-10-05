from pydantic import BaseModel

# Schema cho API Đăng ký khuôn mặt
class EnrollRequest(BaseModel):
    mssv: str
    image_base64: str

# Schema cho API Điểm danh
class CheckInRequest(BaseModel):
    class_id: str
    image_base64: str