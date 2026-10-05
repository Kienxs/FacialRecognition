import os
import shutil
import random
import cv2

SOURCE_DIR = "archive"
DEST_DIR = os.path.join("backend", "ai_service", "dataset")

REAL_KEYWORDS = ["live", "real", "normal"]
SPOOF_KEYWORDS = ["replay", "print", "spoof", "cut", "fake", "attack"]

def setup_directories():
    for split in ['train', 'val']:
        for label in ['real', 'spoof']:
            os.makedirs(os.path.join(DEST_DIR, split, label), exist_ok=True)

def process_file(src_path, dest_dir, label_name, index):
    ext = os.path.splitext(src_path)[1].lower()
    
    # Xử lý nếu là file ảnh
    if ext in ['.jpg', '.jpeg', '.png']:
        new_name = f"{label_name}_{index:05d}{ext}"
        shutil.copy2(src_path, os.path.join(dest_dir, new_name))
        
    # Xử lý nếu là file video (Trích xuất 3 khung hình)
    elif ext in ['.mp4', '.avi', '.mov']:
        cap = cv2.VideoCapture(src_path)
        if not cap.isOpened():
            return
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames > 0:
            step = max(1, total_frames // 4)
            for i in range(1, 4):
                cap.set(cv2.CAP_PROP_POS_FRAMES, i * step)
                ret, frame = cap.read()
                if ret:
                    new_name = f"{label_name}_{index:05d}_f{i}.jpg"
                    cv2.imwrite(os.path.join(dest_dir, new_name), frame)
        cap.release()

def collect_and_split():
    real_files = []
    spoof_files = []

    # Quét cả ảnh và video
    for root, dirs, files in os.walk(SOURCE_DIR):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.mp4', '.avi', '.mov')):
                full_path = os.path.join(root, file)
                folder_lower = root.lower()
                
                if any(kw in folder_lower for kw in REAL_KEYWORDS):
                    real_files.append(full_path)
                elif any(kw in folder_lower for kw in SPOOF_KEYWORDS):
                    spoof_files.append(full_path)

    print(f"Tìm thấy: {len(real_files)} tệp Real, {len(spoof_files)} tệp Spoof.")

    def process_category(file_list, label_name):
        if not file_list:
            print(f"Cảnh báo: Không có dữ liệu cho {label_name}")
            return
        
        # Trộn ngẫu nhiên và chia 80-20
        random.shuffle(file_list)
        train_size = int(len(file_list) * 0.8)
        train_files = file_list[:train_size]
        val_files = file_list[train_size:]

        print(f"Đang trích xuất khung hình cho tập {label_name.upper()}...")
        
        train_dest = os.path.join(DEST_DIR, 'train', label_name)
        for i, f in enumerate(train_files):
            process_file(f, train_dest, label_name, i)
            
        val_dest = os.path.join(DEST_DIR, 'val', label_name)
        for i, f in enumerate(val_files):
            process_file(f, val_dest, label_name, i)

    process_category(real_files, 'real')
    process_category(spoof_files, 'spoof')

if __name__ == "__main__":
    print("Bắt đầu phân loại và cắt video thành ảnh...")
    setup_directories()
    collect_and_split()
    print("Hoàn tất! Cấu trúc dữ liệu đã sẵn sàng để huấn luyện AI.")