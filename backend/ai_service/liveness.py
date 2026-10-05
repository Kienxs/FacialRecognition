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
try:
    model.load_state_dict(torch.load("ai_service/liveness_model.pth", map_location=device))
    model.eval()
except FileNotFoundError:
    print("Cảnh báo: Chưa có file liveness_model.pth")

transform = transforms.Compose([
    transforms.Resize((128, 128)), # Ép chuẩn 128x128 cho mạng CNN
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
])

def check_liveness(face_crop_rgb) -> bool:
    """Nhận vào ảnh crop khuôn mặt (NumPy Array), trả về True (Real) / False (Fake)"""
    # Chuyển NumPy sang PIL Image để dùng torchvision.transforms
    pil_img = Image.fromarray(face_crop_rgb)
    input_tensor = transform(pil_img).unsqueeze(0).to(device)
    
    with torch.no_grad():
        output = model(input_tensor)
        _, predicted = torch.max(output.data, 1)
        
    # Giả định 1 là Real, 0 là Fake 
    return predicted.item() == 1