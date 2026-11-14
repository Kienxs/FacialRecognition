# TÀI LIỆU KỸ THUẬT VÀ KIẾN TRÚC HỆ THỐNG
## HỆ THỐNG ĐIỂM DANH NHẬN DIỆN KHUÔN MẶT THỜI GIAN THỰC (FACIAL RECOGNITION ATTENDANCE)

---

## 1. TỔNG QUAN DỰ ÁN (PROJECT OVERVIEW)

Hệ thống Điểm danh Nhận diện Khuôn mặt là giải pháp ứng dụng công nghệ Thị giác máy tính (Computer Vision) kết hợp Trí tuệ nhân tạo (AI/Deep Learning) để tự động hóa quy trình điểm danh sinh viên trong lớp học.

Hệ thống hoạt động theo mô hình Client-Server:
- **Kiosk Điểm danh (Frontend)**: Chạy trên trình duyệt đặt tại cửa phòng học, liên tục thu thập luồng hình ảnh từ Webcam với tần suất 450ms/lần.
- **Máy chủ AI & Backend**: Tiếp nhận ảnh, thực hiện tiền xử lý ánh sáng (CLAHE), phát hiện khuôn mặt, kiểm định chống giả mạo đa tầng (Anti-Spoofing: Quang học + Động lực học), so khớp khuôn mặt với cơ sở dữ liệu và ghi nhận kết quả điểm danh.
- **Cơ sở dữ liệu**: Lưu trữ thông tin giảng viên, lớp học, sinh viên, các vector đặc trưng khuôn mặt 128 chiều và lịch sử điểm danh với cơ chế chống trùng lặp dữ liệu tuyệt đối.

---

## 2. KIẾN TRÚC VÀ CÔNG NGHỆ SỬ DỤNG (TECH STACK)

### 2.1. Frontend (Giao diện người dùng & Kiosk)
- **Framework**: **React 19** (`react`, `react-dom` 19.2.x).
- **Công cụ xây dựng & Dev Server**: **Vite 8** hỗ trợ Hot Module Replacement (HMR) cực nhanh.
- **Linter**: **Oxlint** (công cụ linting viết bằng Rust siêu nhanh, thay thế ESLint).
- **Xử lý Camera & Luồng hình ảnh**:
  - `navigator.mediaDevices.getUserMedia`: Kết nối trực tiếp Webcam với độ phân giải lý tưởng 1280x720 / 640x480.
  - HTML5 `<canvas>`: Chụp frame video thời gian thực, tự động thu nhỏ kích thước (chiều rộng tối đa 640px) và mã hóa sang dạng chuỗi **JPEG Base64** (chất lượng nén 0.75 - 0.85) nhằm tối ưu băng thông mạng và giảm độ trễ xử lý backend xuống dưới 200ms.
- **Quản lý phiên làm việc**: `sessionStorage` lưu trữ JWT Bearer Token và phiên làm việc của giảng viên.
- **Giao diện & Trải nghiệm (UI/UX)**:
  - Thiết kế CSS thuần hiện đại (Pure CSS / CSS Variables / Flexbox & CSS Grid), hỗ trợ Dark Theme chuyên nghiệp.
  - Cung cấp phản hồi trực quan (Visual Feedback): Khung overlay xanh lá khi nhận diện thành công, overlay đỏ khi phát hiện gian lận, tooltip nhắc nhở chớp mắt tự nhiên.

### 2.2. Backend (API & Xử lý Nghiệp vụ)
- **Ngôn ngữ**: **Python 3.11 / 3.12**.
- **Web Framework**: **FastAPI** – Framework bất đồng bộ (Asynchronous) hiệu năng cao chuẩn ASGI.
- **Web Server**: **Uvicorn** – ASGI web server chạy tại cổng `8000`.
- **ORM & Quản lý CSDL**: **SQLAlchemy 2.x** quản lý cấu trúc bảng, quan hệ thực thể và phiên làm việc (Session).
- **Xác thực & Bảo mật**:
  - `bcrypt`: Băm mật khẩu giảng viên kèm chuỗi ngẫu nhiên (salt).
  - `python-jose`: Cấp phát và giải mã mã thông báo bảo mật **JWT (JSON Web Token)** chuẩn thuật toán `HS256`, thời gian hết hạn 120 phút.
  - `FastAPI OAuth2PasswordBearer`: Dependency bảo vệ các endpoint nhạy cảm (điểm danh, đăng ký, xóa dữ liệu).
- **Kiểm định dữ liệu**: **Pydantic** (`EnrollRequest`, `CheckInRequest`).

### 2.3. AI & Thị giác máy tính (Computer Vision & Deep Learning)
Hệ thống kết hợp các kỹ thuật xử lý ảnh cổ điển và mạng nơ-ron học sâu:
1. **OpenCV (`cv2`)**:
   - Giải mã Base64 sang ma trận NumPy BGR/RGB.
   - **Cân bằng sáng cục bộ CLAHE (Contrast Limited Adaptive Histogram Equalization)**:
     - Tách ảnh sang hệ màu `LAB`.
     - Áp dụng CLAHE trên kênh độ sáng `L` với `clipLimit=2.0, tileGridSize=(8,8)`, giữ nguyên thông tin màu tự nhiên trên 2 kênh `A` và `B`.
     - Giúp hệ thống nhận diện ổn định trong điều kiện phòng học bị ngược sáng hoặc bóng râm.
2. **`face_recognition` (dựa trên thư viện C++ dlib)**:
   - **HOG Face Detector**: Phát hiện vị trí khuôn mặt đa tầng (quét trước trên ảnh thu nhỏ $0.5\times$, fallback lên ảnh gốc $1.0\times$ khi người đứng xa).
   - **68 Facial Landmarks**: Trích xuất 68 điểm mốc đặc trưng trên khuôn mặt (mắt, mày, sống mũi, chóp mũi, môi, đường viền cằm).
   - **128-d Face Embeddings**: Trích xuất vector đặc trưng khuôn mặt gồm 128 số thực.
   - **Khoảng cách Euclidean (`face_distance`)**: So sánh khoảng cách vector giữa khuôn mặt hiện tại và các mẫu đã lưu. Ngưỡng khớp khuôn mặt được cấu hình tối ưu: `FACE_MATCH_THRESHOLD = 0.48`.
3. **PyTorch (`torch`, `torchvision`)**:
   - Kiến trúc mạng nơ-ron tích chập tự thiết kế **LivenessCNN**:
     - `Conv2D(3, 32)` $\rightarrow$ `MaxPool2D` $\rightarrow$ `ReLU`
     - `Conv2D(32, 64)` $\rightarrow$ `MaxPool2D` $\rightarrow$ `ReLU`
     - `Conv2D(64, 128)` $\rightarrow$ `MaxPool2D` $\rightarrow$ `ReLU`
     - `Flatten` $\rightarrow$ `Linear(128*16*16, 512)` $\rightarrow$ `Dropout(0.5)` $\rightarrow$ `Linear(512, 2)` (Real vs Spoof).
     - Phân loại ảnh đầu vào kích thước $128 \times 128$.
4. **Cơ chế chống giả mạo đa tầng (Dual-layer Anti-Spoofing)**:
   - **Tầng 1 - Quang học vật lý (Optical Features)**:
     - **Vân Moiré màn hình (2D FFT)**: Biến đổi Fourier 2D phân tích phổ tần số cao. Màn hình điện thoại/máy tính sẽ tạo ra các dải tần số cao dị thường (`peak_ratio > 3.75`).
     - **Vệt phản quang mặt kính (Specular Glare)**: Phát hiện vùng lóa ánh sáng phản chiếu trên kính thiết bị (`glare_ratio > 0.035`).
     - **Độ sắc nét kết cấu da (Laplacian Sharpness)**: Đo phương sai ma trận Laplacian để phát hiện ảnh giấy in mờ, mất chi tiết hạt da tự nhiên.
     - **Tỷ lệ phổ màu Red/Blue (R/B Ratio)**: Đo quang phổ da người trung tâm; màn hình LED phát quang có kênh Blue cao bất thường (`rb_ratio < 1.06`).
   - **Tầng 2 - Động lực học & Thị sai 3D (Motion & 3D Parallax)**:
     - **Chớp mắt sinh học (Blink Detection)**: Tính chỉ số **EAR (Eye Aspect Ratio)** từ 6 điểm mốc của mỗi mắt. Khi EAR biến thiên $\ge 0.038$ và độ mở mắt giảm $\ge 15\%$, xác nhận người thật `CONFIRMED_LIVE`.
     - **Thị sai 3D phi tuyến (Non-Rigid / 3D Parallax Residual)**: Áp dụng thuật toán bình phương tối thiểu (Least Squares) khớp phép biến đổi phẳng 2D Affine giữa các frame liên tiếp.
       - Nếu cầm màn hình/ảnh phẳng lắc qua lại: sai số biến đổi phẳng rất nhỏ ($< 0.85\text{px}$) $\rightarrow$ phát hiện gian lận `2D Planar Spoof`.
       - Nếu là khuôn mặt thật 3D (có độ nhô chóp mũi, biến dạng biểu cảm môi): sai số biến dạng 3D lớn ($\ge 1.20\text{px}$) $\rightarrow$ xác nhận người thật `CONFIRMED_LIVE`.
       - Nếu là ảnh bất động hoàn toàn sau 2.8 giây $\rightarrow$ kết luận `STATIC SPOOF`.

---

## 3. LUỒNG DỮ LIỆU VÀ QUY TRÌNH HOẠT ĐỘNG (FLOW DETAILS)

### 3.1. Quy trình khởi động hệ thống (`run_all.py`)
1. Kích hoạt script `backend/seed.py`:
   - Kiểm tra và tự động khởi tạo tài khoản Giảng viên mặc định: `GV001` (Mật khẩu: `123456`).
   - Khởi tạo lớp học mẫu `CS101` (Nhập môn CNTT).
   - Khởi tạo danh sách 8 sinh viên mẫu và gán vào lớp `CS101`.
2. Khởi chạy tiến trình con chạy Backend FastAPI trên cổng `8000`.
3. Khởi chạy tiến trình con chạy Frontend Vite React trên cổng `5173`.
4. Đợi 3 giây và tự động mở trình duyệt web mặc định tại địa chỉ `http://localhost:5173`.
5. Đóng cả 2 tiến trình an toàn khi bấm `Ctrl + C`.

---

### 3.2. Quy trình Đăng nhập & Điều hướng (Authentication Flow)
1. Giảng viên truy cập giao diện, nhập Mã giảng viên và Mật khẩu.
2. Frontend gửi request `POST /api/auth/login` (hoặc `/api/teachers/login`).
3. Backend:
   - Truy vấn bảng `teachers` theo mã ID.
   - Dùng `bcrypt.checkpw` đối soát mật khẩu với mã băm `password_hash`.
   - Nếu đúng, đóng gói `sub=teacher_id` và sinh chuỗi JWT Bearer Token.
4. Frontend lưu trữ Token vào `sessionStorage` và chuyển sang màn hình **Dashboard**.

---

### 3.3. Quy trình Đăng ký khuôn mặt sinh viên (Enrollment Flow)
```
[Webcam] ──(Base64)──> [POST /api/students/enroll] 
                           │
                           ├── 1. Kiểm tra / Tạo hồ sơ sinh viên trong DB
                           ├── 2. Cân bằng sáng CLAHE & Cắt ảnh mặt (HOG)
                           ├── 3. Kiểm tra liveness quang học cơ bản (liveness_score >= 0.35)
                           ├── 4. Trích xuất 128-d Face Vector (num_jitters=2)
                           ├── 5. Lưu vào bảng face_embeddings (tối đa 3 vector/sinh viên)
                           └── 6. Trả về thông báo thành công cho Frontend
```

---

### 3.4. Quy trình Điểm danh Kiosk thời gian thực (Real-time Kiosk Check-in Flow)

```
[Camera Kiosk] 
      │ (Định kỳ mỗi 450ms, kiểm tra khóa isProcessing)
      ▼
[POST /api/attendance/checkin]
      │
      ├── BƯỚC 1: XỬ LÝ KHUNG HÌNH (Process Face Pipeline)
      │     ├── Decode Base64 -> Cân bằng sáng CLAHE
      │     ├── Quét HOG: Phát hiện 0 mặt -> Báo "NO_FACE"
      │     ├── Quét HOG: Phát hiện >= 2 mặt -> Báo "MULTIPLE_FACES"
      │     └── Trích xuất 68 Landmarks và Face Vector 128 chiều
      │
      ├── BƯỚC 2: KIỂM ĐỊNH QUANG HỌC VẬT LÝ & AI (Optical Liveness)
      │     ├── 2D FFT phát hiện Moiré màn hình
      │     ├── Phản quang kính màn hình + R/B ratio phát quang LED
      │     ├── Laplacian variance kiểm tra độ phẳng/mờ
      │     ├── Suy luận qua mạng LivenessCNN (nếu có model)
      │     └── NẾU CÓ DẤU HIỆU GIẢ MẠO:
      │           └── Trả về "SPOOF_WARNING" (Frontend hiển thị Cảnh báo)
      │
      ├── BƯỚC 3: SO KHỚP KHUÔN MẶT (Face Matching)
      │     ├── Tải toàn bộ Face Embeddings trong Database
      │     ├── Tính khoảng cách Euclidean: distances = face_distance(known_encodings, current)
      │     ├── min_dist = min(distances)
      │     └── NẾU min_dist > 0.48:
      │           └── Trả về "UNKNOWN" (Chưa nhận diện được)
      │
      ├── BƯỚC 4: KIỂM ĐỊNH ĐỘNG LỰC HỌC CỬ ĐỘNG SỐNG (Motion Liveness)
      │     ├── Ghi nhận lịch sử (Landmarks, EAR, timestamp) vào RAM Cache (_SESSION_CACHE)
      │     ├── [Trường hợp A]: Phát hiện chớp mắt thật (EAR biến thiên >= 0.038)
      │     │     └── Đạt "CONFIRMED_LIVE" -> Đi tiếp tới Bước 5
      │     ├── [Trường hợp B]: Phát hiện cử động 3D / Thị sai thật (Residual >= 1.20px)
      │     │     └── Đạt "CONFIRMED_LIVE" -> Đi tiếp tới Bước 5
      │     ├── [Trường hợp C]: Điện thoại quay nghiêng phẳng (Residual < 0.85px, Move >= 4px)
      │     │     └── Chặn ngay "CONFIRMED_SPOOF" (Phát hiện gian lận mặt phẳng 2D)
      │     ├── [Trường hợp D]: Ảnh tĩnh hoàn toàn qua 2.8 giây
      │     │     └── Chặn ngay "CONFIRMED_SPOOF" (Phát hiện ảnh tĩnh)
      │     └── [Trường hợp E]: Đang trong quá trình theo dõi
      │           └── Trả về "VERIFYING" (Frontend hiện: "Vui lòng chớp mắt tự nhiên")
      │
      └── BƯỚC 5: GHI NHẬN ĐIỂM DANH VÀO CƠ SỞ DỮ LIỆU
            ├── Lấy ngày hiện tại theo múi giờ Việt Nam (Asia/Ho_Chi_Minh)
            ├── Kiểm tra trong bảng attendance_records theo (mssv, class_id, attendance_date)
            ├── Nếu chưa có: INSERT bản ghi mới với status="SUCCESS", face_distance, liveness_score
            └── Trả về: { success: true, status: "SUCCESS", mssv, name, face_distance }
```

---

## 4. THIẾT KẾ CƠ SỞ DỮ LIỆU (DATABASE ARCHITECTURE)

- **Hệ quản trị CSDL**: **SQLite** (tập tin `attendance.db`).
- **ORM**: SQLAlchemy Declarative Base.

### 4.1. Chi tiết các bảng dữ liệu

#### 1. Bảng `teachers` (Giảng viên)
| Cột | Kiểu dữ liệu | Khóa | Ràng buộc | Diễn giải |
| :--- | :--- | :--- | :--- | :--- |
| `id` | VARCHAR | PK | NOT NULL, Index | Mã giảng viên (Ví dụ: `GV001`) |
| `name` | VARCHAR | | NOT NULL | Họ và tên giảng viên |
| `password_hash` | VARCHAR | | NOT NULL | Chuỗi mật khẩu băm bảo mật bằng bcrypt |

#### 2. Bảng `classes` (Lớp học)
| Cột | Kiểu dữ liệu | Khóa | Ràng buộc | Diễn giải |
| :--- | :--- | :--- | :--- | :--- |
| `id` | VARCHAR | PK | NOT NULL, Index | Mã lớp học (Ví dụ: `CS101`) |
| `name` | VARCHAR | | NOT NULL | Tên môn học / học phần |
| `teacher_id` | VARCHAR | FK | REFERENCES `teachers(id)` | Giảng viên phụ trách lớp |

#### 3. Bảng `students` (Sinh viên)
| Cột | Kiểu dữ liệu | Khóa | Ràng buộc | Diễn giải |
| :--- | :--- | :--- | :--- | :--- |
| `mssv` | VARCHAR | PK | NOT NULL, Index | Mã số sinh viên (Ví dụ: `20210001`) |
| `name` | VARCHAR | | NOT NULL | Họ và tên sinh viên |

#### 4. Bảng trung gian `class_students` (Liên kết N-N Lớp - Sinh viên)
| Cột | Kiểu dữ liệu | Khóa | Ràng buộc | Diễn giải |
| :--- | :--- | :--- | :--- | :--- |
| `class_id` | VARCHAR | PK, FK | REFERENCES `classes(id)` | Mã lớp học |
| `mssv` | VARCHAR | PK, FK | REFERENCES `students(mssv)` | Mã sinh viên |

#### 5. Bảng `face_embeddings` (Vector đặc trưng khuôn mặt)
| Cột | Kiểu dữ liệu | Khóa | Ràng buộc | Diễn giải |
| :--- | :--- | :--- | :--- | :--- |
| `id` | INTEGER | PK | Autoincrement | ID tự tăng |
| `mssv` | VARCHAR | FK | REFERENCES `students(mssv)` | Mã sinh viên sở hữu khuôn mặt |
| `encoding_json` | VARCHAR | | NOT NULL | Chuỗi JSON mảng số thực 128 chiều |
| `quality_score` | FLOAT | | NULLABLE | Điểm chất lượng ảnh khi đăng ký |

> *Ghi chú thiết kế*: Một sinh viên có thể lưu trữ tối đa 3 vector đặc trưng (chính diện, nghiêng nhẹ, ánh sáng khác nhau) để nâng cao độ nhận diện trong các góc chụp khác nhau. Hỗ trợ `cascade="all, delete-orphan"` (khi xóa sinh viên thì tự động xóa hết vector).

#### 6. Bảng `attendance_records` (Lịch sử điểm danh)
| Cột | Kiểu dữ liệu | Khóa | Ràng buộc | Diễn giải |
| :--- | :--- | :--- | :--- | :--- |
| `id` | INTEGER | PK | Autoincrement | ID bản ghi |
| `mssv` | VARCHAR | FK | NOT NULL, REFERENCES `students(mssv)` | Sinh viên được điểm danh |
| `class_id` | VARCHAR | FK | NOT NULL, REFERENCES `classes(id)` | Lớp học được điểm danh |
| `attendance_date` | DATE | | NOT NULL | Ngày điểm danh (múi giờ Việt Nam) |
| `timestamp` | DATETIME | | NOT NULL | Dấu thời gian chính xác (UTC) |
| `status` | VARCHAR | | NOT NULL | Trạng thái (`SUCCESS`, `SPOOF_DETECTED`, ...) |
| `face_distance` | FLOAT | | NULLABLE | Khoảng cách Euclidean khuôn mặt đo được |
| `liveness_score` | FLOAT | | NULLABLE | Điểm người thật tại thời điểm quét |
| `spoof_type` | VARCHAR | | NULLABLE | Chi tiết gian lận phát hiện (nếu có) |

> *Ràng buộc chống trùng lặp dữ liệu*:
> ```sql
> CONSTRAINT uq_attendance_per_day UNIQUE (mssv, class_id, attendance_date)
> ```
> Ràng buộc này đảm bảo một sinh viên **chỉ có thể điểm danh thành công 1 lần duy nhất trong ngày đối với một lớp học**, ngăn chặn triệt để tình trạng spam request, lỗi duplicate hoặc race condition từ nhiều frame gửi lên đồng thời.

---

### 4.2. Sơ đồ Thực thể Liên kết (Entity-Relationship Diagram)

```
   ┌──────────────┐             1:N              ┌──────────────┐
   │   teachers   │ ──────────────────────────── │   classes    │
   └──────────────┘                              └──────────────┘
                                                        │ 1:N
                                                        │
                                                        ▼
   ┌──────────────┐             N:N              ┌──────────────┐
   │   students   │ ◀══════════════════════════▶ │class_students│
   └──────────────┘                              └──────────────┘
     │          │
 1:N │          │ 1:N
     ▼          ▼
┌──────────────┐  ┌────────────────────┐
│face_embedding│  │ attendance_records │
└──────────────┘  └────────────────────┘
```

---

## 5. HƯỚNG DẪN VẬN HÀNH VÀ THƯ MỤC NGUỒN

### 5.1. Cấu trúc thư mục dự án
```
FacialRecognition/
├── attendance.db                      # Cơ sở dữ liệu SQLite cấp ngoài
├── FacialRecognition/
│   ├── run_all.py                     # Script một chạm bật toàn bộ hệ thống
│   ├── prepare_dataset.py             # Script xử lý dữ liệu huấn luyện Liveness
│   ├── generate_model.py              # Script tạo file trọng số khởi tạo
│   ├── archive/                       # Dữ liệu ảnh/video chống giả mạo mẫu
│   │
│   ├── backend/                       # MÃ NGUỒN BACKEND (FastAPI + AI)
│   │   ├── main.py                    # Khởi tạo App, định tuyến toàn bộ API
│   │   ├── database.py                # Kết nối SQLite & Session Dependency
│   │   ├── models.py                  # Định nghĩa ORM Database Models
│   │   ├── schemas.py                 # Pydantic Schemas
│   │   ├── security.py                # Xử lý mật khẩu bcrypt & JWT Token
│   │   ├── seed.py                    # Khởi tạo dữ liệu mẫu GV001 & CS101
│   │   ├── attendance.db              # Database SQLite hoạt động chính
│   │   └── ai_service/                # DỊCH VỤ XỬ LÝ AI
│   │       ├── face_engine.py         # Pipeline CLAHE, HOG & 128-d Vector
│   │       ├── liveness.py            # Chống gian lận quang học & LivenessCNN
│   │       ├── motion_liveness.py     # Chống gian lận động lực học (EAR + 3D)
│   │       ├── train_model.py         # Huấn luyện PyTorch LivenessCNN
│   │       └── liveness_model.pth     # File trọng số PyTorch
│   │
│   └── frontend/                      # MÃ NGUỒN FRONTEND (React 19 + Vite)
│       ├── package.json               # Cấu hình thư viện React, Vite, Oxlint
│       ├── vite.config.js             # Cấu hình Vite
│       └── src/
│           ├── main.jsx               # Entry point ứng dụng React
│           ├── App.jsx                # Router điều hướng trạng thái phiên
│           ├── LoginPage.jsx          # Màn hình đăng nhập Giảng viên
│           ├── DashboardPage.jsx      # Màn hình chọn lớp & điều khiển
│           ├── KioskPage.jsx          # Màn hình Kiosk điểm danh thời gian thực
│           ├── EnrollModal.jsx        # Hộp thoại đăng ký khuôn mặt mới
│           ├── StudentManageModal.jsx # Quản lý danh sách & Xóa khuôn mặt
│           └── index.css              # Giao diện Dark theme chuyên nghiệp
```

### 5.2. Lệnh khởi chạy hệ thống
Chỉ cần chạy một lệnh duy nhất tại thư mục dự án:
```powershell
python FacialRecognition\run_all.py
```
- **Tài khoản đăng nhập mặc định**: `GV001`
- **Mật khẩu**: `123456`
- **Địa chỉ giao diện Kiosk**: `http://localhost:5173`
- **Tài liệu API Swagger**: `http://127.0.0.1:8000/docs`

---
*Tài liệu kỹ thuật được khởi tạo và cập nhật tự động từ cấu trúc mã nguồn thực tế của dự án.*
