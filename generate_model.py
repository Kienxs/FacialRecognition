import torch
import torch.nn as nn
import torch.nn.functional as F
import os

# Copy đúng kiến trúc mạng CNN từ liveness.py của bạn
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

if __name__ == "__main__":
    print("Khởi tạo mạng CNN chống gian lận...")
    model = LivenessCNN()
    
    # Chỉ định đường dẫn lưu vào thư mục ai_service
    save_dir = os.path.join("backend", "ai_service")
    os.makedirs(save_dir, exist_ok=True)
    
    save_path = os.path.join(save_dir, "liveness_model.pth")
    torch.save(model.state_dict(), save_path)
    
    print(f"Thành công! Đã tạo file trọng số AI tại: {save_path}")
    print("Lưu ý: Đây chỉ là model ngẫu nhiên để API chạy được. Cần Train với dataset thật để chống spoofing.")