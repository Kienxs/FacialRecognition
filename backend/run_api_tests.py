import urllib.request
import urllib.error
import json

BASE_URL = "http://127.0.0.1:8000"

def request_json(path, method="GET", data=None, token=None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        
    req_data = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))

def test_api():
    print("=" * 70)
    print("      KIỂM THỬ TÍCH HỢP HỆ THỐNG QUA REST API")
    print("=" * 70)
    
    # 1. Login sai mật khẩu
    code1, res1 = request_json("/api/teachers/login", "POST", {"username": "GV001", "password": "wrongpassword"})
    print(f"1. Login sai mật khẩu: Code={code1} -> {'PASS' if code1 == 401 else 'FAIL'}")
    
    # 2. Login đúng mật khẩu
    code2, res2 = request_json("/api/teachers/login", "POST", {"username": "GV001", "password": "123456"})
    token = res2.get("access_token")
    print(f"2. Login đúng mật khẩu: Code={code2}, Token={'Có' if token else 'Không'} -> {'PASS' if token else 'FAIL'}")
    
    # 3. Lấy danh sách lớp
    code3, res3 = request_json("/api/classes", "GET", token=token)
    print(f"3. Lấy danh sách lớp: Code={code3}, Số lớp={len(res3)} -> {'PASS' if len(res3) > 0 else 'FAIL'}")
    
    # 4. Gửi frame ảnh không có mặt
    code4, res4 = request_json("/api/attendance/checkin", "POST", {
        "class_id": "CS101",
        "image_base64": "data:image/jpeg;base64,/9j/4AAQSkZJRg=="
    }, token=token)
    print(f"4. Gửi frame ảnh rỗng/lỗi: Status={res4.get('status')} -> {'PASS' if res4.get('status') == 'NO_FACE' else 'FAIL'}")
    print("=" * 70)

if __name__ == "__main__":
    test_api()
