import { useEffect, useRef, useState } from "react";

// Possible states for the check-in flow
const STATUS = {
  IDLE: "idle",
  CHECKING: "checking",
  SUCCESS: "success",
  FAIL: "fail",
};

export default function CheckInPage({ user, onLogout }) {
  const videoRef = useRef(null);
  const streamRef = useRef(null); // keep a ref to the stream so we can stop it on unmount
  const [status, setStatus] = useState(STATUS.IDLE);
  const [message, setMessage] = useState("");
  const [cameraError, setCameraError] = useState(null);

  // Start the camera once when the component mounts
  useEffect(() => {
    async function startCamera() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "user" },
          audio: false,
        });
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
      } catch (err) {
        // Common causes: no camera, permission denied, or not on https/localhost
        setCameraError(
          "Không thể mở camera. Kiểm tra quyền truy cập camera của trình duyệt."
        );
        console.error(err);
      }
    }
    startCamera();

    // Cleanup: stop all tracks when component unmounts, otherwise camera stays "on"
    return () => {
      streamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  // Fake check-in call — replace this with a real API call once BE has an endpoint
  function handleCheckIn() {
    setStatus(STATUS.CHECKING);
    setMessage("");

    setTimeout(() => {
      // TODO: swap this mock with fetch("/api/checkin", { method: "POST", body: <frame capture> })
      const isSuccess = Math.random() > 0.3; // fake 70% success rate for demo
      if (isSuccess) {
        setStatus(STATUS.SUCCESS);
        setMessage("Điểm danh thành công!");
      } else {
        setStatus(STATUS.FAIL);
        setMessage("Không xác thực được. Vui lòng thử lại.");
      }
    }, 1200); // simulate network/processing delay
  }

  return (
    <div style={styles.container}>
      <div style={styles.topBar}>
        <span>MSSV: {user?.username}</span>
        <button type="button" onClick={onLogout} style={styles.logout}>
          Đăng xuất
        </button>
      </div>
      <h1 style={styles.title}>Điểm danh</h1>

      <div style={styles.videoWrapper}>
        {cameraError ? (
          <div style={styles.errorBox}>{cameraError}</div>
        ) : (
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            style={styles.video}
          />
        )}
      </div>

      <button
        onClick={handleCheckIn}
        disabled={status === STATUS.CHECKING || cameraError}
        style={styles.button}
      >
        {status === STATUS.CHECKING ? "Đang kiểm tra..." : "Check-in"}
      </button>

      {message && (
        <div
          style={{
            ...styles.result,
            color: status === STATUS.SUCCESS ? "#16a34a" : "#dc2626",
          }}
        >
          {message}
        </div>
      )}
    </div>
  );
}

// Plain inline styles for now — swap for CSS modules / Tailwind later once core logic works
const styles = {
  container: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 16,
    padding: 24,
    fontFamily: "sans-serif",
  },
  topBar: {
    width: "100%",
    maxWidth: 480,
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    fontSize: 14,
    color: "#475569",
  },
  logout: {
    padding: "6px 12px",
    fontSize: 14,
    borderRadius: 6,
    border: "1px solid #cbd5e1",
    background: "white",
    cursor: "pointer",
  },
  title: { margin: 0 },
  videoWrapper: {
    width: 480,
    height: 360,
    background: "#000",
    borderRadius: 8,
    overflow: "hidden",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  video: { width: "100%", height: "100%", objectFit: "cover" },
  errorBox: { color: "white", padding: 16, textAlign: "center" },
  button: {
    padding: "10px 24px",
    fontSize: 16,
    borderRadius: 6,
    border: "none",
    background: "#2563eb",
    color: "white",
    cursor: "pointer",
  },
  result: { fontSize: 18, fontWeight: 600 },
};
