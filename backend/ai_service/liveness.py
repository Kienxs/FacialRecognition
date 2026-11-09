# ai_service/liveness.py
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.transforms as transforms
from PIL import Image

class LivenessCNN(nn.Module):
    def __init__(self):
        super(LivenessCNN, self).__init__()
        self.conv1 = nn.Conv2d(3, 32, 3, padding=1)
        self.pool1 = nn.MaxPool2d(2, 2)
        self.conv2 = nn.Conv2d(32, 64, 3, padding=1)
        self.pool2 = nn.MaxPool2d(2, 2)
        self.conv3 = nn.Conv2d(64, 128, 3, padding=1)
        self.pool3 = nn.MaxPool2d(2, 2)
        self.fc1 = nn.Linear(128 * 16 * 16, 512)
        self.dropout = nn.Dropout(0.5)
        self.fc2 = nn.Linear(512, 2)

    def forward(self, x):
        x = self.pool1(F.relu(self.conv1(x)))
        x = self.pool2(F.relu(self.conv2(x)))
        x = self.pool3(F.relu(self.conv3(x)))
        x = x.view(-1, 128 * 16 * 16)
        x = F.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.fc2(x)
        return x

# Load model global để tối ưu tốc độ API
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = LivenessCNN().to(device)
import os

MODEL_PATH = os.path.join(os.path.dirname(__file__), "liveness_model.pth")
try:
    if os.path.exists(MODEL_PATH):
        model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
        model.eval()
    else:
        print(f"Cảnh báo: Chưa có file {MODEL_PATH}")
except Exception as e:
    print(f"Cảnh báo khi tải liveness model: {e}")

transform = transforms.Compose([
    transforms.Resize((128, 128)), # Ép chuẩn 128x128 cho mạng CNN
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
])

import cv2
import numpy as np

def analyze_spoof_features(face_crop_rgb):
    """
    Phân tích dấu hiệu giả mạo vật lý:
    1. Vân Moiré tần số cao (màn hình điện thoại/máy tính).
    2. Độ phản quang bề mặt kính/giấy (Specular glare).
    3. Độ chi tiết kết cấu da tự nhiên (Laplacian sharpness).
    """
    gray = cv2.cvtColor(face_crop_rgb, cv2.COLOR_RGB2GRAY)
    resized_gray = cv2.resize(gray, (128, 128))
    
    # 1. 2D FFT tìm Moiré Pattern (Đặc trưng của màn hình LCD/OLED)
    f = np.fft.fft2(resized_gray.astype(np.float32))
    fshift = np.fft.fftshift(f)
    magnitude = 20 * np.log(np.abs(fshift) + 1e-8)
    
    cy, cx = 64, 64
    r = 20
    y, x = np.ogrid[:128, :128]
    mask = (x - cx)**2 + (y - cy)**2 > r**2
    
    high_freq_vals = magnitude[mask]
    mean_hf = np.mean(high_freq_vals)
    max_hf = np.max(high_freq_vals)
    std_hf = np.std(high_freq_vals) + 1e-6
    peak_ratio = (max_hf - mean_hf) / std_hf
    
    # 2. Laplacian Variance (Độ tương phản và độ mịn kết cấu)
    laplacian_var = cv2.Laplacian(resized_gray, cv2.CV_64F).var()
    
    # 3. Phản quang mặt kính điện thoại (vùng cháy sáng chói lóa)
    glare_mask = resized_gray > 248
    glare_ratio = np.sum(glare_mask) / (128.0 * 128.0)
    
    # 4. Phân tích quang phổ phát quang màn hình (Backlight Blue Light Emission)
    # Da người thật phản xạ ánh sáng tự nhiên với sắc tố đỏ/ấm trội (R > B rất nhiều).
    # Màn hình LCD/OLED phát quang qua đèn nền LED làm tăng vọt kênh Blue.
    r_mean = float(np.mean(face_crop_rgb[:, :, 0]))
    b_mean = float(np.mean(face_crop_rgb[:, :, 2]))
    rb_ratio = r_mean / (b_mean + 1e-5)
    
    reasons = []
    # 1. Phát hiện màn hình điện thoại / máy tính qua vân Moiré tần số cao
    # Theo dữ liệu thực nghiệm: Người thật ~ 2.9 - 3.1, Màn hình điện thoại ~ 3.4 - 3.8
    if peak_ratio > 3.30:
        reasons.append(f"Phát hiện lưới pixel / Moiré màn hình điện thoại (Moiré: {peak_ratio:.2f})")
        
    # 2. Phát hiện phản quang chói sáng từ mặt kính điện thoại / ảnh ép bóng
    if glare_ratio > 0.030:
        reasons.append("Phát hiện vệt phản quang mặt kính màn hình")
        
    # 3. Phát hiện ảnh in phẳng / ảnh quá mờ
    if laplacian_var < 18.0:
        reasons.append("Ảnh phẳng mất kết cấu da tự nhiên")
        
    # 4. Phát hiện ánh sáng phát quang đèn LED màn hình
    if rb_ratio < 1.10:
        reasons.append("Phát hiện ánh sáng phát quang màn hình điện tử")
        
    is_spoof = len(reasons) > 0
    return is_spoof, reasons, peak_ratio, glare_ratio, laplacian_var, rb_ratio

def check_liveness(face_crop_rgb):
    """
    Nhận vào ảnh crop khuôn mặt (NumPy Array), trả về (is_real: bool, score: float, detail: str)
    Dựa trên phân tích kết cấu quang học và quang phổ tần số Moiré thực tế.
    """
    is_spoof_feat, reasons, peak_ratio, glare_ratio, lap_var, rb_ratio = analyze_spoof_features(face_crop_rgb)
    
    # Tính điểm số Liveness thực tế (từ 0.0 đến 1.0)
    penalty = max(0.0, (peak_ratio - 3.0) * 0.4) + (glare_ratio * 4.0)
    calculated_score = float(max(0.05, min(0.98, 0.95 - penalty)))
    
    is_real = not is_spoof_feat
    
    print(f"[AI LIVENESS] Score: {calculated_score:.2f} | Moiré: {peak_ratio:.2f} | R/B: {rb_ratio:.2f} | Glare: {glare_ratio:.3f} | Sharpness: {lap_var:.1f} -> {'LIVE' if is_real else 'SPOOF DETECTED'}")
    
    if not is_real:
        detail_msg = ", ".join(reasons)
        return False, calculated_score, detail_msg
        
    return True, calculated_score, "Người thật (Live)"