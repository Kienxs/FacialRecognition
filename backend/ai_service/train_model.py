import os
import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms
from torch.utils.data import DataLoader
from ai_service.liveness import LivenessCNN

DATASET_DIR = os.path.join(os.path.dirname(__file__), "dataset")
MODEL_PATH = os.path.join(os.path.dirname(__file__), "liveness_model.pth")

data_transforms = {
    'train': transforms.Compose([
        transforms.Resize((128, 128)),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5])
    ]),
    'val': transforms.Compose([
        transforms.Resize((128, 128)),
        transforms.ToTensor(),
        transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5])
    ]),
}

def train():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Bắt đầu huấn luyện mô hình Liveness trên {device}...")
    
    # Dataset loader
    # Classes: ['real', 'spoof'] -> class_to_idx: {'real': 0, 'spoof': 1}
    train_dir = os.path.join(DATASET_DIR, 'train')
    val_dir = os.path.join(DATASET_DIR, 'val')
    
    train_dataset = datasets.ImageFolder(train_dir, data_transforms['train'])
    val_dataset = datasets.ImageFolder(val_dir, data_transforms['val'])
    
    print("Class mapping:", train_dataset.class_to_idx)
    # Quy ước: 1 là Real, 0 là Spoof.
    # Nếu default ImageFolder gán real: 0, spoof: 1 -> Ta map lại hoặc train nhãn tương ứng.
    # Đảm bảo index 1 = real, 0 = spoof:
    
    train_loader = DataLoader(train_dataset, batch_size=16, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=16, shuffle=False)
    
    model = LivenessCNN().to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    real_idx = train_dataset.class_to_idx.get('real', 0)
    spoof_idx = train_dataset.class_to_idx.get('spoof', 1)
    
    # Ta chuẩn hoá label sao cho: Target 1 = Real, Target 0 = Spoof
    epochs = 25
    for epoch in range(epochs):
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0
        
        for inputs, labels in train_loader:
            inputs = inputs.to(device)
            # Chuyển đổi nhãn: 1 = real, 0 = spoof
            mapped_labels = torch.where(labels == real_idx, torch.tensor(1), torch.tensor(0)).to(device)
            
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, mapped_labels)
            loss.backward()
            optimizer.step()
            
            running_loss += loss.item() * inputs.size(0)
            _, preds = torch.max(outputs, 1)
            correct += (preds == mapped_labels).sum().item()
            total += mapped_labels.size(0)
            
        acc = correct / total if total > 0 else 0
        if (epoch + 1) % 5 == 0 or epoch == epochs - 1:
            print(f"Epoch [{epoch+1}/{epochs}] - Loss: {running_loss/total:.4f} - Train Acc: {acc*100:.2f}%")
            
    # Lưu trọng số mô hình đã train
    torch.save(model.state_dict(), MODEL_PATH)
    print(f"✅ Hoàn tất huấn luyện! Trọng số đã lưu tại: {MODEL_PATH}")

if __name__ == "__main__":
    train()
