# 🎓 Hệ Thống Điểm Danh Sinh Viên Bằng Nhận Diện Khuôn Mặt (Facial Recognition Attendance System)

Ứng dụng web điểm danh sinh viên thông minh theo thời gian thực sử dụng **Trí tuệ nhân tạo (AI)**, tích hợp cơ chế **chống giả mạo 2 lớp (Dual-layer Liveness Detection)**, giao diện **Kiosk điểm danh tự động**, quản lý dữ liệu khuôn mặt và hỗ trợ **xuất báo cáo Excel**.

---

## 📌 Mục lục
- [Tính năng nổi bật](#-tính-năng-nổi-bật)
- [Kiến trúc & Công nghệ](#-kiến-trúc--công-nghệ)
- [Cơ chế AI & Chống gian lận](#-cơ-chế-ai--chống-gian-lận)
- [Cấu trúc thư mục](#-cấu-trúc-thư-mục)
- [Hướng dẫn cài đặt & Khởi chạy](#-hướng-dẫn-cài-đặt--khởi-chạy)
  - [1. Yêu cầu hệ thống](#1-yêu-cầu-hệ-thống)
  - [2. Cài đặt và khởi chạy Backend](#2-cài-đặt-và-khởi-chạy-backend)
  - [3. Cài đặt và khởi chạy Frontend](#3-cài-đặt-và-khởi-chạy-frontend)
- [Tài khoản thử nghiệm](#-tài-khoản-thử-nghiệm)
- [Danh sách API Endpoints](#-danh-sách-api-endpoints)
- [Ghi chú phát triển](#-ghi-chú-phát-triển)

---

## ✨ Tính năng nổi bật

- 🔐 **Xác thực giảng viên phân quyền**: Đăng nhập an toàn qua chuẩn **OAuth2 Password Flow** & **JWT Token**, mật khẩu mã hóa bằng thuật toán `bcrypt`.
- 📷 **Chế độ Kiosk điểm danh tự động (Auto-Attendance Kiosk)**:
  - Tự động bắt khung hình camera theo thời gian thực (chu kỳ ~450ms).
  - Nhận diện khuôn mặt sinh viên và hiển thị kết quả trực quan ngay trên màn hình.
  - Tự động ngăn trùng lặp: Mỗi sinh viên chỉ được ghi nhận một lần cho mỗi ca học/ngày.
- 🛡️ **Chống giả mạo 2 lớp (Dual-layer Liveness Detection)**:
  - **Lớp 1 - Passive Liveness (Quang học)**: Phân tích tần số không gian 2D FFT (phát hiện lưới pixel / vân Moiré màn hình điện thoại), độ phản quang mặt kính, độ nét kết cấu da (Laplacian variance) và tỷ lệ phổ màu.
  - **Lớp 2 - Active Liveness (Cử động & Chớp mắt)**: Theo dõi biến thiên tỷ lệ khung mắt (Eye Aspect Ratio - EAR) và vi rung chuyển động người thật theo chuỗi khung hình để loại trừ ảnh tĩnh in trên giấy hoặc video replay góc cố định.
- 👤 **Quản lý sinh viên & Đăng ký khuôn mặt (Enrollment)**:
  - Chụp ảnh trực tiếp từ webcam để trích xuất 128-dimensional embedding lưu trữ vào cơ sở dữ liệu.
  - Hỗ trợ xem danh sách sinh viên lớp và xóa dữ liệu nhận diện để đăng ký lại khi cần.
- 📊 **Tổng kết & Xuất báo cáo điểm danh ra Excel**:
  - Khi giảng viên bấm kết thúc ca điểm danh, hệ thống tự động hiển thị modal tổng kết (Tổng số có mặt, Đúng giờ, Đi trễ).
  - Tải trực tiếp bảng danh sách điểm danh định dạng file `.csv` (tương thích 100% với Microsoft Excel, Google Sheets).
- 📱 **Hỗ trợ truy cập mạng LAN & HTTPS**:
  - Cấu hình Vite Dev Server với `host: true` và plugin `@vitejs/plugin-basic-ssl` cho phép điện thoại, máy tính bảng hoặc laptop khác trong mạng Wi-Fi truy cập camera và sử dụng kiosk điểm danh.

---

## 🛠️ Kiến trúc & Công nghệ

### 1. Backend (API & AI Service)
* **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.10+) - Hiệu năng cao, async/await, tự động sinh tài liệu Swagger/OpenAPI.
* **Database & ORM**: SQLite + [SQLAlchemy 2.0](https://www.sqlalchemy.org/).
* **Bảo mật**: `python-jose` (JWT Tokens), `passlib` & `bcrypt` (mã hóa mật khẩu).
* **AI & Thị giác máy tính**:
  * [OpenCV](https://opencv.org/): Tiền xử lý ảnh, cân bằng tương phản thích ứng (CLAHE), phân tích phổ FFT.
  * [dlib](http://dlib.net/) & [face_recognition](https://github.com/ageitgey/face_recognition): Trích xuất 68 điểm mốc đặc trưng (Landmarks) và 128 chiều vector khuôn mặt (ResNet embedding).
  * [PyTorch](https://pytorch.org/): Huấn luyện và hỗ trợ mô hình học sâu CNN phân loại ảnh giả mạo.

### 2. Frontend (Client Kiosk)
* **Thư viện & Nền tảng**: [React 19](https://react.dev/), [Vite 8](https://vitejs.dev/).
* **Giao diện**: Thiết kế Dark Mode hiện đại (Glassmorphism), đáp ứng mượt mà trên nhiều kích thước màn hình.
* **Camera Streaming**: HTML5 `<video>` & `<canvas>` API xử lý ảnh Base64 nén gửi định kỳ.
* **Mạng & Bảo mật**: `@vitejs/plugin-basic-ssl` phục vụ HTTPS cho WebRTC/Camera trên thiết bị di động, Vite Proxy định tuyến an toàn `/api` về Backend.

---

## 🧠 Cơ chế AI & Chống gian lận

```
  [Camera Kiosk]
        │
        ▼ (Base64 JPEG Frame)
┌─────────────────────────────────────────────────────────────┐
│  Multi-stage Face Detection (face_engine.py)                │
│  ├─ Stage 1: Quét nhanh HOG upsample=0                      │
│  ├─ Stage 2: Thử nghiệm ảnh thu nhỏ tỷ lệ 0.5               │
│  ├─ Stage 3: Cân bằng tương phản thích ứng (CLAHE bù sáng)   │
│  ├─ Stage 4: Thử lật gương (Mirror Webcam)                  │
│  └─ Stage 5 & Fallback: CNN Face Detector                   │
└─────────────────────────────────────────────────────────────┘
        │
        ├─► Không thấy mặt ──► Báo lỗi NO_FACE
        ├─► Nhiều hơn 1 mặt ──► Báo lỗi MULTIPLE_FACES
        ▼ (Tách 1 khuôn mặt hợp lệ)
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: Passive Liveness (liveness.py)                   │
│  ├─ 2D FFT Moiré Ratio: Phát hiện lưới ma trận pixel LCD    │
│  ├─ Glare Ratio: Phát hiện vệt phản chiếu mặt kính màn hình │
│  ├─ Laplacian Variance: Kiểm tra độ sâu kết cấu da          │
│  └─ Red/Blue Channel Ratio: Phát hiện quang phổ màn hình LED│
└─────────────────────────────────────────────────────────────┘
        │
        ├─► Dính bẫy giả mạo ──► Trả về SPOOF_WARNING
        ▼ (Vượt qua kiểm tra quang học)
┌─────────────────────────────────────────────────────────────┐
│  Vector Matching (face_engine.py)                           │
│  └─ So khớp Euclidean Distance với Database (ngưỡng 0.55)   │
└─────────────────────────────────────────────────────────────┘
        │
        ├─► Không khớp ──► Trả về UNKNOWN (Khách / Chưa đăng ký)
        ▼ (Đúng MSSV sinh viên)
┌─────────────────────────────────────────────────────────────┐
│  Layer 2: Active Motion Liveness (motion_liveness.py)       │
│  ├─ Eye Aspect Ratio (EAR): Tính độ mở/nhắm mắt qua 68 mốc  │
│  ├─ Micro-motion Displacement: Theo dõi vi rung cơ mặt thật │
│  └─ Multi-frame Cache: Theo dõi chuỗi 3–10 frames liên tục │
└─────────────────────────────────────────────────────────────┘
        │
        ├─► Đang theo dõi ──► Yêu cầu: "Vui lòng chớp mắt..."
        ├─► Bất động hoàn toàn ──► Phát hiện ảnh tĩnh (SPOOF)
        ▼ (Xác nhận người thật)
┌─────────────────────────────────────────────────────────────┐
│  Ghi nhận Điểm danh (AttendanceRecord)                      │
│  └─ Lưu MSSV, Lớp, Ngày, Giờ vào SQLite DB & Phản hồi Kiosk │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 Cấu trúc thư mục

```text
FacialRecognition/
├── backend/
│   ├── ai_service/
│   │   ├── face_engine.py          # Pipeline trích xuất mặt, CLAHE, landmarks & 128D embedding
│   │   ├── liveness.py             # Heuristic kiểm tra quang học chống giả mạo (FFT, Glare, Laplacian)
│   │   ├── motion_liveness.py      # Đánh giá liveness qua chớp mắt (EAR) và chuyển động
│   │   ├── train_model.py          # Script huấn luyện mô hình PyTorch CNN (Real vs Spoof)
│   │   └── liveness_model.pth      # Checkpoint trọng số mô hình liveness
│   ├── attendance.db               # Cơ sở dữ liệu SQLite cục bộ (lưu lớp, sinh viên, embeddings, điểm danh)
│   ├── database.py                 # Cấu hình SQLAlchemy engine & SessionLocal
│   ├── models.py                   # Định nghĩa ORM Models (Teacher, Student, Class, AttendanceRecord, ...)
│   ├── schemas.py                  # Pydantic schemas kiểm thực dữ liệu đầu vào/ra
│   ├── security.py                 # Hàm băm mật khẩu, mã hóa và giải mã JWT Token
│   ├── seed.py                     # Script tạo tài khoản mẫu (GV001) và danh sách sinh viên ban đầu
│   ├── main.py                     # Khởi tạo FastAPI App & toàn bộ RESTful Endpoints
│   └── requirements.txt            # Danh sách gói phụ thuộc Python
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx                 # Điều hướng ứng dụng theo trạng thái phiên làm việc
│   │   ├── LoginPage.jsx           # Màn hình đăng nhập tài khoản giảng viên
│   │   ├── DashboardPage.jsx       # Trang chủ quản lý lớp, danh sách sinh viên và chọn ca Kiosk
│   │   ├── KioskPage.jsx           # Màn hình Kiosk điểm danh thời gian thực, tổng kết & xuất file CSV
│   │   ├── EnrollModal.jsx         # Modal chụp ảnh đăng ký khuôn mặt sinh viên mới
│   │   ├── StudentManageModal.jsx  # Modal quản lý danh sách và xóa embedding sinh viên
│   │   └── index.css               # Định dạng màu sắc, Glassmorphism, animations Dark Mode
│   ├── package.json                # Cấu hình phụ thuộc Node.js (React 19, basic-ssl, Vite)
│   └── vite.config.js              # Cấu hình Vite Dev Server, Basic SSL và Proxy `/api`
│
├── run_all.py                      # Script tự động khởi chạy cả Backend và Frontend chỉ bằng 1 lệnh
├── README.md                       # Tài liệu hướng dẫn sử dụng và triển khai dự án
└── .gitignore                      # Cấu hình loại trừ tệp nhị phân và môi trường ảo
```

---

## 🚀 Hướng dẫn cài đặt & Khởi chạy

### 1. Yêu cầu hệ thống
* **Hệ điều hành**: Windows 10/11, macOS hoặc Linux.
* **Python**: Phiên bản `3.10` trở lên (Khuyến nghị 3.10 hoặc 3.11).
* **Node.js**: Phiên bản `18.x` hoặc `20.x` trở lên (kèm `npm`).
* **Visual C++ Build Tools** *(dành riêng cho Windows)*: Cần thiết để biên dịch gói `dlib` và `face_recognition`.

---

### 2. Cài đặt các gói phụ thuộc (Thực hiện lần đầu tiên)

#### Bước 2.1: Cài đặt Backend
Mở terminal tại thư mục gốc dự án:
```powershell
# Di chuyển vào backend
cd backend

# Tạo và kích hoạt môi trường ảo
python -m venv venv
.\venv\Scripts\Activate.ps1    # Trên Windows PowerShell
# source venv/bin/activate     # Trên Linux / macOS

# Nâng cấp pip và cài đặt thư viện
pip install --upgrade pip
pip install -r requirements.txt
```
*(Nếu cài đặt `dlib` trên Windows gặp lỗi biên dịch, bạn có thể cài bản dựng sẵn siêu nhanh: `pip install dlib-bin`)*.

#### Bước 2.2: Cài đặt Frontend
Mở một cửa sổ terminal mới:
```powershell
# Di chuyển vào frontend
cd frontend

# Cài đặt các gói npm
npm install
```

---

### 3. Khởi chạy ứng dụng

#### ⚡ Cách 1: Khởi chạy nhanh 1 chạm với `run_all.py` (Khuyến nghị)

Tại thư mục gốc dự án (`FacialRecognition/`), bạn chỉ cần chạy một lệnh duy nhất:

```powershell
python run_all.py
```

> [!TIP]
> **Điểm nổi bật của `run_all.py`:**
> - **Chống xung đột cổng mạng**: Tự động phát hiện và giải phóng cổng `8000` nếu có tiến trình chạy ngầm cũ đang chiếm giữ, triệt tiêu hoàn toàn lỗi `[WinError 10013]`.
> - **Tự động nhận diện môi trường ảo**: Tự động phát hiện và sử dụng `backend/venv/Scripts/python.exe` mà không cần bạn phải nhớ kích hoạt thủ công.
> - **Khởi tạo dữ liệu mẫu**: Tự động chạy `seed.py` để tạo tài khoản giảng viên `GV001` và lớp học mẫu `CS101`.
> - **Bật đồng thời 2 tiến trình**: Mở Backend FastAPI tại `http://127.0.0.1:8000` và Frontend Vite tại `https://localhost:5173`.
> - **Tự động mở trình duyệt**: Sau 3 giây khi hệ thống sẵn sàng, trình duyệt sẽ tự động mở giao diện điểm danh.
> - **Dọn dẹp an toàn**: Nhấn `Ctrl + C` tại Terminal để đóng sạch sẽ cả Backend và Frontend cùng lúc.

---

#### 🛠️ Cách 2: Khởi chạy thủ công từng phần (Dành cho việc debug riêng)

Nếu bạn muốn theo dõi log chi tiết của từng dịch vụ trong các cửa sổ riêng biệt:

* **Cửa sổ 1 - Chạy Backend FastAPI:**
  ```powershell
  cd backend
  .\venv\Scripts\Activate.ps1
  python seed.py                                                    # Khởi tạo dữ liệu mẫu
  python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload  # Chạy server API
  ```
  * Swagger Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

* **Cửa sổ 2 - Chạy Frontend Vite:**
  ```powershell
  cd frontend
  npm run dev
  ```
  * Truy cập Kiosk tại máy: `https://localhost:5173`
  * Truy cập từ điện thoại / tablet qua Wi-Fi: `https://<IP_MAY_TINH>:5173`

> [!NOTE]
> Do Vite sử dụng chứng chỉ HTTPS tự ký (`@vitejs/plugin-basic-ssl`) để cấp quyền Camera/WebRTC trên mạng LAN, trình duyệt sẽ hiển thị cảnh báo chứng chỉ ở lần đầu truy cập. Bạn chỉ cần chọn **"Nâng cao" (Advanced) → "Tiếp tục truy cập" (Proceed)**.

---

## 🔑 Tài khoản thử nghiệm

Dữ liệu mẫu sau khi chạy `python seed.py`:

| Loại tài khoản | Tên đăng nhập | Mật khẩu | Lớp học mẫu |
|---|---|---|---|
| **Giảng viên (Teacher)** | `GV001` | `123456` | `CS101 - Nhập môn CNTT` |

*Hệ thống đã có sẵn danh sách các sinh viên mẫu (20210001, 20210015, 20210023, ...). Giảng viên có thể vào Dashboard, bấm **"Đăng ký khuôn mặt"** để gán mặt thực tế cho từng bạn.*

---

## 📡 Danh sách API Endpoints

| Phương thức | Đường dẫn API | Xác thực | Chức năng |
|:---:|:---|:---:|:---|
| `POST` | `/api/auth/login` | Không | Đăng nhập giảng viên, nhận access_token JWT |
| `GET` | `/api/students` | Không | Lấy danh sách toàn bộ sinh viên và trạng thái có khuôn mặt |
| `POST` | `/api/students/enroll` | Bearer Token | Đăng ký ảnh khuôn mặt mới cho sinh viên |
| `DELETE` | `/api/students/{mssv}/face` | Bearer Token | Xóa vector đặc trưng khuôn mặt của sinh viên |
| `POST` | `/api/attendance/checkin` | Bearer Token | Xử lý frame camera kiosk: kiểm tra liveness & điểm danh |
| `GET` | `/` | Không | Kiểm tra trạng thái hoạt động (Health check) |

---

## 📝 Ghi chú phát triển

1. **Vị trí chạy Backend**: Đường dẫn kết nối SQLite trong code là `sqlite:///./attendance.db`. Luôn thực thi lệnh chạy backend từ thư mục `backend/` để đảm bảo kết nối đúng file cơ sở dữ liệu.
2. **Xuất báo cáo Excel**: Định dạng file CSV được mã hóa UTF-8 với ký tự BOM (`\uFEFF`) để đảm bảo các ký tự tiếng Việt có dấu hiển thị chuẩn xác khi mở trực tiếp trong Microsoft Excel.
3. **Môi trường huấn luyện**: Trong thư mục `backend/ai_service/`, script `train_model.py` hỗ trợ huấn luyện mạng CNN trên tập dữ liệu ảnh Real/Spoof nếu muốn mở rộng thêm lớp kiểm tra học sâu trong tương lai.

---

⭐ *Đồ án được xây dựng và phát triển phục vụ học tập, nghiên cứu và ứng dụng thực tiễn trong quản lý điểm danh giảng đường.*
