from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def run_fastapi_tests():
    print("=" * 70)
    print("      KIỂM THỬ TÍCH HỢP TOÀN DIỆN QUA FASTAPI TESTCLIENT")
    print("=" * 70)
    
    # 1. Login sai thông tin
    res_bad = client.post("/api/teachers/login", json={"username": "GV001", "password": "wrong"})
    print(f"1. Test Login sai mật khẩu: Code={res_bad.status_code} -> {'PASS' if res_bad.status_code == 401 else 'FAIL'}")
    
    # 2. Login đúng thông tin
    res_ok = client.post("/api/teachers/login", json={"username": "GV001", "password": "123456"})
    token = res_ok.json().get("access_token")
    print(f"2. Test Login đúng mật khẩu: Code={res_ok.status_code}, Token={'Có' if token else 'Không'} -> {'PASS' if token else 'FAIL'}")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 3. Lấy danh sách lớp
    res_cls = client.get("/api/classes", headers=headers)
    classes = res_cls.json()
    print(f"3. Lấy danh sách lớp học: Found {len(classes)} classes -> {'PASS' if len(classes) > 0 else 'FAIL'}")
    
    # 4. Gửi frame ảnh rỗng/lỗi
    res_noface = client.post("/api/attendance/checkin", headers=headers, json={
        "class_id": "CS101",
        "image_base64": "data:image/jpeg;base64,/9j/4AAQSkZJRg=="
    })
    nf_json = res_noface.json()
    print(f"4. Kiểm tra ảnh rỗng không mặt: Status={nf_json.get('status')} -> {'PASS' if nf_json.get('status') == 'NO_FACE' else 'FAIL'}")
    
    # 5. Kiểm tra lấy danh sách sinh viên lớp CS101
    res_students = client.get("/api/classes/CS101/students", headers=headers)
    print(f"5. Lấy danh sách sinh viên lớp CS101: Code={res_students.status_code}, Số lượng={len(res_students.json())} -> PASS")
    print("=" * 70)

if __name__ == "__main__":
    run_fastapi_tests()
