import { useEffect, useRef, useState } from "react";

export default function EnrollModal({ teacher, onClose, onSuccess }) {
  const [mssv, setMssv] = useState("");
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null); // { type: 'success' | 'error', text: '' }
  const [cameraError, setCameraError] = useState(null);

  const videoRef = useRef(null);
  const streamRef = useRef(null);

  useEffect(() => {
    async function startCamera() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "user", width: { ideal: 640 }, height: { ideal: 480 } },
          audio: false,
        });
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
      } catch (err) {
        setCameraError("Không thể mở camera. Vui lòng cấp quyền truy cập camera.");
        console.error(err);
      }
    }
    startCamera();

    return () => {
      streamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  async function handleCaptureAndEnroll(e) {
    e.preventDefault();
    if (!mssv.trim()) {
      setMessage({ type: "error", text: "Vui lòng nhập Mã số sinh viên (MSSV)." });
      return;
    }
    if (!videoRef.current || videoRef.current.videoWidth === 0) {
      setMessage({ type: "error", text: "Camera chưa sẵn sàng." });
      return;
    }

    setLoading(true);
    setMessage(null);

    // Chụp ảnh từ webcam
    const canvas = document.createElement("canvas");
    canvas.width = videoRef.current.videoWidth;
    canvas.height = videoRef.current.videoHeight;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
    const base64Image = canvas.toDataURL("image/jpeg", 0.85);

    try {
      const response = await fetch("http://127.0.0.1:8000/api/students/enroll", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${teacher.token}`,
        },
        body: JSON.stringify({
          mssv: mssv.trim().toUpperCase(),
          name: name.trim() || undefined,
          image_base64: base64Image,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setMessage({
          type: "success",
          text: data.message || `Đã đăng ký thành công cho sinh viên ${name || mssv}!`,
        });
        if (onSuccess) onSuccess({ mssv: mssv.trim().toUpperCase(), name: name.trim() });
      } else {
        setMessage({
          type: "error",
          text: data.detail || "Đăng ký khuôn mặt không thành công. Hãy thử lại.",
        });
      }
    } catch (err) {
      console.error(err);
      setMessage({ type: "error", text: "Không thể kết nối đến máy chủ AI Backend." });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={modalStyles.backdrop}>
      <div className="card fade-in" style={modalStyles.modal}>
        <div style={modalStyles.header}>
          <h2 style={modalStyles.title}>📸 Đăng ký định danh & khuôn mặt</h2>
          <button type="button" onClick={onClose} style={modalStyles.closeBtn}>✕</button>
        </div>

        <form onSubmit={handleCaptureAndEnroll} style={modalStyles.body}>
          <div style={modalStyles.fieldGroup}>
            <label style={modalStyles.label}>Mã số sinh viên (MSSV) *</label>
            <input
              type="text"
              className="input"
              value={mssv}
              onChange={(e) => setMssv(e.target.value)}
              placeholder="VD: 20219999"
              required
              disabled={loading}
            />
          </div>

          <div style={modalStyles.fieldGroup}>
            <label style={modalStyles.label}>Họ và tên sinh viên</label>
            <input
              type="text"
              className="input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="VD: Đoàn Khánh"
              disabled={loading}
            />
          </div>

          {/* Camera preview */}
          <div style={modalStyles.cameraWrapper}>
            {cameraError ? (
              <div style={modalStyles.cameraError}>{cameraError}</div>
            ) : (
              <>
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  muted
                  style={modalStyles.video}
                />
                <div style={modalStyles.faceGuide}>
                  <div style={modalStyles.faceGuideOval} />
                  <span style={modalStyles.faceGuideText}>Đặt khuôn mặt vào giữa khung hình</span>
                </div>
              </>
            )}
          </div>

          {message && (
            <div
              style={{
                ...modalStyles.alert,
                backgroundColor: message.type === "success" ? "rgba(34, 197, 94, 0.15)" : "rgba(239, 68, 68, 0.15)",
                borderColor: message.type === "success" ? "#22c55e" : "#ef4444",
                color: message.type === "success" ? "#4ade80" : "#f87171",
              }}
            >
              {message.text}
            </div>
          )}

          <div style={modalStyles.actions}>
            <button
              type="button"
              className="btn btn-ghost"
              onClick={onClose}
              disabled={loading}
            >
              Đóng
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading || cameraError}
              style={{ minWidth: 160 }}
            >
              {loading ? "Đang xử lý AI..." : "📸 Chụp & Đăng ký"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

const modalStyles = {
  backdrop: {
    position: "fixed",
    inset: 0,
    backgroundColor: "rgba(0, 0, 0, 0.75)",
    backdropFilter: "blur(8px)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    zIndex: 9999,
    padding: 16,
  },
  modal: {
    width: "100%",
    maxWidth: 520,
    maxHeight: "92vh",
    overflowY: "auto",
    padding: 24,
    borderRadius: "var(--radius-lg, 16px)",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 20,
  },
  title: {
    fontSize: 20,
    fontWeight: 700,
    margin: 0,
  },
  closeBtn: {
    background: "transparent",
    border: "none",
    color: "var(--text-muted)",
    fontSize: 20,
    cursor: "pointer",
    padding: "4px 8px",
  },
  body: {
    display: "flex",
    flexDirection: "column",
    gap: 16,
  },
  fieldGroup: {
    display: "flex",
    flexDirection: "column",
    gap: 6,
  },
  label: {
    fontSize: 13,
    fontWeight: 600,
    color: "var(--text-secondary)",
  },
  cameraWrapper: {
    position: "relative",
    width: "100%",
    height: 280,
    borderRadius: "var(--radius-md, 12px)",
    overflow: "hidden",
    backgroundColor: "#000",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  video: {
    width: "100%",
    height: "100%",
    objectFit: "cover",
    transform: "scaleX(-1)", // Lật camera dạng gương
  },
  cameraError: {
    color: "var(--danger)",
    padding: 16,
    textAlign: "center",
    fontSize: 14,
  },
  faceGuide: {
    position: "absolute",
    inset: 0,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    pointerEvents: "none",
  },
  faceGuideOval: {
    width: 170,
    height: 220,
    border: "2px dashed rgba(255, 255, 255, 0.6)",
    borderRadius: "50%",
    boxShadow: "0 0 20px rgba(0, 0, 0, 0.5)",
  },
  faceGuideText: {
    marginTop: 8,
    fontSize: 12,
    color: "rgba(255, 255, 255, 0.8)",
    textShadow: "0 1px 3px rgba(0,0,0,0.8)",
  },
  alert: {
    padding: "10px 14px",
    borderRadius: "var(--radius-sm, 8px)",
    border: "1px solid transparent",
    fontSize: 13,
    lineHeight: 1.4,
  },
  actions: {
    display: "flex",
    justifyContent: "flex-end",
    gap: 12,
    marginTop: 8,
  },
};
