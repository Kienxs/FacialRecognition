# ai_service/liveness.py
import os
import cv2
import numpy as np
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

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = LivenessCNN().to(device)
MODEL_LOADED = False

MODEL_PATH = os.path.join(os.path.dirname(__file__), "liveness_model.pth")
try:
    if os.path.exists(MODEL_PATH):
        model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
        model.eval()
        MODEL_LOADED = True
    else:
        print(f"Cảnh báo: Chưa có file {MODEL_PATH}, sử dụng chế độ Quang học thuần túy.")
except Exception as e:
    print(f"Cảnh báo khi tải liveness model: {e}")

transform = transforms.Compose([
    transforms.Resize((128, 128)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
])

def analyze_spoof_features(face_crop_rgb):
    """
    Phân tích dấu hiệu giả mạo vật lý trên vùng lõi khuôn mặt (tránh nhiễu nền và tóc):
    1. Vân Moiré tần số cao (2D FFT).
    2. Độ phản quang bề mặt kính/giấy (Specular glare).
    3. Độ chi tiết kết cấu da (Laplacian sharpness).
    4. Phổ phát quang đèn nền màn hình (R/B ratio trên vùng da trung tâm).
    """
    gray = cv2.cvtColor(face_crop_rgb, cv2.COLOR_RGB2GRAY)
    resized_gray = cv2.resize(gray, (128, 128))
    resized_rgb = cv2.resize(face_crop_rgb, (128, 128))

    # Cắt vùng lõi da mặt trung tâm (loại bỏ rìa tóc đen và nền tường)
    roi_rgb = resized_rgb[20:108, 20:108]
    roi_gray = resized_gray[20:108, 20:108]

    # 1. 2D FFT tìm Moiré Pattern
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
    peak_ratio = float((max_hf - mean_hf) / std_hf)

    # 2. Laplacian Variance
    laplacian_var = float(cv2.Laplacian(resized_gray, cv2.CV_64F).var())

    # 3. Phản quang mặt kính điện thoại (đo trên vùng trung tâm và toàn khung)
    glare_mask = resized_gray > 250
    glare_ratio = float(np.sum(glare_mask) / (128.0 * 128.0))

    # 4. Tỷ lệ R/B trên vùng da trung tâm (tránh bị tóc đen ở viền kéo giảm R)
    r_mean = float(np.mean(roi_rgb[:, :, 0]))
    b_mean = float(np.mean(roi_rgb[:, :, 2]))
    rb_ratio = float(r_mean / (b_mean + 1e-5))

    reasons = []
    risk_points = 0.0

    # Ngưỡng Moiré màn hình
    if peak_ratio > 3.75:
        reasons.append(f"Phát hiện lưới pixel / Moiré màn hình điện thoại (Moiré: {peak_ratio:.2f})")
        risk_points += 1.0 if peak_ratio > 3.50 else 0.65

    # Ngưỡng chói lóa mặt kính
    if glare_ratio > 0.035:
        reasons.append("Phát hiện vệt phản quang mặt kính màn hình")
        risk_points += 1.0 if glare_ratio > 0.050 else 0.70

    # Ngưỡng mất kết cấu da (chỉ phạt nặng khi ảnh cực mờ < 12.0)
    if laplacian_var < 12.0:
        reasons.append("Ảnh phẳng mất kết cấu da tự nhiên")
        risk_points += 0.80

    # Ngưỡng phát quang màn hình LED (kênh Blue cao bất thường so với Red)
    if rb_ratio < 1.06:
        reasons.append("Phát hiện ánh sáng phát quang màn hình điện tử")
        risk_points += 1.0 if rb_ratio < 1.02 else 0.65

    is_spoof = risk_points >= 0.70
    return is_spoof, reasons, peak_ratio, glare_ratio, laplacian_var, rb_ratio

def check_liveness(face_crop_rgb):
    """
    Kết hợp phân tích Quang học Vật lý và Mạng học sâu LivenessCNN (nếu có trọng số).
    """
    is_spoof_feat, reasons, peak_ratio, glare_ratio, lap_var, rb_ratio = analyze_spoof_features(face_crop_rgb)

    # Điểm quang học cơ sở
    penalty = max(0.0, (peak_ratio - 3.1) * 0.35) + (glare_ratio * 3.5)
    if rb_ratio < 1.06:
        penalty += (1.10 - rb_ratio) * 1.5
    optical_score = float(max(0.05, min(0.98, 0.95 - penalty)))

    # Kết hợp với dự đoán từ LivenessCNN nếu model đã được train
    cnn_score = optical_score
    if MODEL_LOADED:
        try:
            pil_img = Image.fromarray(face_crop_rgb)
            tensor_in = transform(pil_img).unsqueeze(0).to(device)
            with torch.no_grad():
                outputs = model(tensor_in)
                probs = F.softmax(outputs, dim=1)
                cnn_score = float(probs[0, 1].item()) # Index 1 = Real
        except Exception:
            cnn_score = optical_score

    # Nếu vi phạm quang học rõ rệt (is_spoof_feat = True), ưu tiên chặn ngay
    if is_spoof_feat:
        calculated_score = min(optical_score, cnn_score * 0.5)
        is_real = False
    else:
        calculated_score = 0.65 * optical_score + 0.35 * cnn_score
        is_real = calculated_score >= 0.45

    print(
        f"[AI LIVENESS] Score: {calculated_score:.2f} (Opt: {optical_score:.2f}, CNN: {cnn_score:.2f}) | "
        f"Moiré: {peak_ratio:.2f} | R/B: {rb_ratio:.2f} | Glare: {glare_ratio:.3f} | "
        f"Sharpness: {lap_var:.1f} -> {'LIVE' if is_real else 'SPOOF DETECTED'}"
    )

    if not is_real:
        detail_msg = ", ".join(reasons) if reasons else "Phát hiện dấu hiệu giả mạo từ mô hình AI"
        return False, calculated_score, detail_msg

    return True, calculated_score, "Người thật (Live)"