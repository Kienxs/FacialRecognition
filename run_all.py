import os
import sys
import time
import webbrowser
import subprocess

def get_project_root():
    """Tự động tìm thư mục chứa backend và frontend dù đặt file ở lớp trong hay lớp ngoài"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.exists(os.path.join(current_dir, "backend")) and os.path.exists(os.path.join(current_dir, "frontend")):
        return current_dir
    nested_dir = os.path.join(current_dir, "FacialRecognition")
    if os.path.exists(os.path.join(nested_dir, "backend")):
        return nested_dir
    return current_dir

def free_port(port: int):
    """Tự động giải phóng cổng nếu có tiến trình chạy ngầm cũ đang chiếm giữ"""
    try:
        if os.name == "nt":
            output = subprocess.check_output(f"netstat -ano | findstr :{port}", shell=True).decode()
            current_pid = str(os.getpid())
            for line in output.strip().splitlines():
                parts = line.strip().split()
                if len(parts) >= 5 and "LISTENING" in parts:
                    pid = parts[-1]
                    if pid != "0" and pid != current_pid:
                        print(f"⚠️  Cổng {port} đang bị tiến trình cũ (PID {pid}) chiếm giữ, đang tự động giải phóng...")
                        subprocess.run(f"taskkill /F /PID {pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        time.sleep(0.5)
    except Exception:
        pass

def main():
    root_dir = get_project_root()
    backend_dir = os.path.join(root_dir, "backend")
    frontend_dir = os.path.join(root_dir, "frontend")
    venv_python = os.path.join(backend_dir, "venv", "Scripts", "python.exe") if os.name == "nt" else os.path.join(backend_dir, "venv", "bin", "python")
    python_exe = venv_python if os.path.exists(venv_python) else sys.executable
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"

    print("=" * 65)
    print("🚀 ĐANG KHỞI ĐỘNG TOÀN BỘ HỆ THỐNG ĐIỂM DANH NHẬN DIỆN KHUÔN MẶT")
    print("=" * 65)

    # 1. Tự động kiểm tra và giải phóng cổng 8000 tránh xung đột WinError 10013 / 10048
    free_port(8000)

    # 2. Tự động chạy seed.py để đảm bảo có sẵn tài khoản GV001 và lớp CS101
    seed_script = os.path.join(backend_dir, "seed.py")
    if os.path.exists(seed_script):
        print("🔹 [1/3] Đang kiểm tra & khởi tạo dữ liệu mẫu (seed.py)...")
        subprocess.run([python_exe, "seed.py"], cwd=backend_dir)

    processes = []
    try:
        # 3. Khởi chạy Backend FastAPI (Port 8000)
        print("🔹 [2/3] Đang bật Backend FastAPI tại http://127.0.0.1:8000 ...")
        backend_proc = subprocess.Popen(
            [python_exe, "-m", "uvicorn", "main:app", "--reload", "--port", "8000"],
            cwd=backend_dir
        )
        processes.append(backend_proc)

        # 4. Khởi chạy Frontend Vite (Port 5173)
        print("🔹 [3/3] Đang bật Frontend React + Vite tại https://localhost:5173 ...")
        frontend_proc = subprocess.Popen(
            [npm_cmd, "run", "dev"],
            cwd=frontend_dir
        )
        processes.append(frontend_proc)

        # Đợi 3 giây cho server lên rồi tự động mở trình duyệt
        time.sleep(3)
        print("\n✅ HỆ THỐNG ĐÃ SẴN SÀNG! Đang mở trình duyệt...")
        print("👉 Tài khoản: GV001 | Mật khẩu: 123456")
        print("⚠️  Nhấn Ctrl + C tại Terminal này để tắt đồng thời cả Backend và Frontend.\n")
        webbrowser.open("https://localhost:5173")

        # Giữ tiến trình chạy cho đến khi bấm Ctrl + C
        while True:
            time.sleep(1)
            if backend_proc.poll() is not None:
                print(f"⚠️  Backend đã dừng (mã thoát: {backend_proc.poll()}). Đang đóng hệ thống...")
                break
            if frontend_proc.poll() is not None:
                print(f"⚠️  Frontend đã dừng (mã thoát: {frontend_proc.poll()}). Đang đóng hệ thống...")
                break

    except KeyboardInterrupt:
        print("\n🛑 Đang tắt toàn bộ Backend và Frontend...")
    finally:
        for p in processes:
            if p.poll() is None:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    p.terminate()
        print("✅ Đã đóng toàn bộ hệ thống an toàn!")

if __name__ == "__main__":
    main()
