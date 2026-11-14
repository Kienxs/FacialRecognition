import { useEffect, useRef, useState, useCallback } from "react";

// ── Mock student data ──
const MOCK_STUDENTS = [
  { mssv: "20210001", name: "Lê Minh Tuấn" },
  { mssv: "20210015", name: "Nguyễn Thị Hoa" },
  { mssv: "20210023", name: "Trần Đức Anh" },
  { mssv: "20210037", name: "Phạm Thanh Hằng" },
  { mssv: "20210042", name: "Vũ Hoàng Long" },
  { mssv: "20210056", name: "Đỗ Thị Mai" },
  { mssv: "20210064", name: "Hoàng Văn Sơn" },
  { mssv: "20210078", name: "Bùi Ngọc Linh" },
];

function formatTime(date) {
  return date.toLocaleTimeString("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

// ── Component ──────────────────────────────────────────────
export default function KioskPage({ teacher, classInfo, onEndSession, onLogout }) {
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const listEndRef = useRef(null);

  const [cameraError, setCameraError] = useState(null);
  const [checkins, setCheckins] = useState([]);
  const [elapsed, setElapsed] = useState(0);
  const [startTime] = useState(() => new Date());

  // The overlay result shown on the camera when someone checks in
  const [overlay, setOverlay] = useState(null); // { name, mssv, success }
  const overlayTimer = useRef(null);
  const [verifyingHint, setVerifyingHint] = useState(null);
  const hintTimeoutRef = useRef(null);
  const [showSummaryModal, setShowSummaryModal] = useState(false);

  // Xuất file CSV/Excel UTF-8 có BOM
  function exportToExcel() {
    const todayStr = new Date().toLocaleDateString("vi-VN").replace(/\//g, "-");
    const headers = ["STT", "Mã số sinh viên", "Họ và tên", "Thời gian điểm danh", "Trạng thái"];
    const rows = checkins.map((c, index) => [
      index + 1,
      `="${c.mssv}"`, // Format dạng text trong Excel tránh mất số 0
      `"${c.name.replace(/"/g, '""')}"`,
      formatTime(new Date(c.time)),
      "Có mặt"
    ]);

    const csvContent = "\uFEFF" + [
      [`DANH SÁCH ĐIỂM DANH LỚP: ${classInfo.id} - ${classInfo.name}`],
      [`Ngày: ${todayStr}`, `Phòng: ${classInfo.room}`, `Giảng viên: ${teacher.name}`],
      [],
      headers,
      ...rows,
      [],
      ["Tổng số điểm danh:", checkins.length]
    ].map(e => e.join(",")).join("\n");

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `DiemDanh_${classInfo.id}_${todayStr}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    onEndSession();
  }



  // ── Start camera ──
  useEffect(() => {
    async function startCamera() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 720 } },
          audio: false,
        });
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
      } catch (err) {
        setCameraError(
          "Không thể mở camera. Kiểm tra quyền truy cập camera của trình duyệt."
        );
        console.error("Camera error:", err);
      }
    }
    startCamera();

    return () => {
      streamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  // ── Elapsed timer ──
  useEffect(() => {
    const interval = setInterval(() => {
      setElapsed((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  // ── Show overlay for 1.8 seconds ──
  const showCheckInOverlay = useCallback((student, success) => {
    if (overlayTimer.current) clearTimeout(overlayTimer.current);
    setOverlay({ ...student, success });
    overlayTimer.current = setTimeout(() => {
      setOverlay(null);
      overlayTimer.current = null; // Bắt buộc giải phóng để cho phép quét tiếp!
    }, 1800);
  }, []);

  const isProcessing = useRef(false); // Khóa (lock) để tránh gửi request chồng chéo

  useEffect(() => {
    const captureAndSendFrame = async () => {
      // 1. Chặn nếu chưa có camera, đang hiện overlay, video chưa load xong, hoặc đang đợi API cũ trả về
      if (
        !videoRef.current ||
        videoRef.current.videoWidth === 0 || 
        overlayTimer.current !== null ||
        isProcessing.current
      ) {
        return;
      }

      isProcessing.current = true; // Bật khóa luồng

      // Tối ưu kích thước ảnh (rộng tối đa 640px) để gửi nhanh và AI nhận diện dưới 0.2s
      const video = videoRef.current;
      const maxDim = 640;
      let width = video.videoWidth;
      let height = video.videoHeight;
      if (width > maxDim) {
        height = Math.round((height * maxDim) / width);
        width = maxDim;
      }

      const canvas = document.createElement("canvas");
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext("2d");
      ctx.drawImage(video, 0, 0, width, height);
      
      const base64Image = canvas.toDataURL("image/jpeg", 0.75);

      try {
        const response = await fetch("/api/attendance/checkin", {
          method: "POST",
          headers: { 
            "Content-Type": "application/json",
            "Authorization": `Bearer ${teacher.token}`
          },
          body: JSON.stringify({ 
            class_id: classInfo.id, 
            image_base64: base64Image 
          }),
        });

        const result = await response.json();

        if (result.success) {
          setVerifyingHint(null);
          showCheckInOverlay({ name: result.name, mssv: result.mssv }, true);
          setCheckins((prev) => {
            if (prev.some((c) => c.mssv === result.mssv)) return prev;
            return [...prev, { mssv: result.mssv, name: result.name, time: new Date() }];
          });
        } else if (result.status === "VERIFYING") {
          // Hiện gợi ý nhẹ nhàng cho người dùng tự nhiên chớp mắt
          setVerifyingHint("👁️ Vui lòng nhìn tự nhiên hoặc chớp mắt");
          if (hintTimeoutRef.current) clearTimeout(hintTimeoutRef.current);
          hintTimeoutRef.current = setTimeout(() => setVerifyingHint(null), 1200);
        } else if (result.status === "SPOOF_WARNING") {
          setVerifyingHint(null);
          showCheckInOverlay({ 
            name: "CẢNH BÁO GIAN LẬN", 
            mssv: result.detail || "Hình ảnh không hợp lệ. Vui lòng xác thực người thật." 
          }, false);
        } else if (result.status === "UNKNOWN") {
          setVerifyingHint(null);
          if (result.detail && !result.detail.includes("Không phát hiện")) {
            showCheckInOverlay({ 
              name: "Chưa nhận diện được", 
              mssv: "Khuôn mặt chưa có trong dữ liệu" 
            }, false);
          }
        }
      } catch (err) {
        console.error("Lỗi AI Backend:", err);
      } finally {
        isProcessing.current = false; // Tắt khóa, cho phép request tiếp theo chạy
      }
    };

    const interval = setInterval(captureAndSendFrame, 450);
    return () => clearInterval(interval);
  }, [classInfo.id, teacher.token, showCheckInOverlay]); // Khai báo rõ classInfo.id thay vì classInfo object

  // ── Auto-scroll check-in list ──
  useEffect(() => {
    listEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [checkins]);

  // ── Cleanup overlay timer on unmount ──
  useEffect(() => {
    return () => {
      if (overlayTimer.current) clearTimeout(overlayTimer.current);
    };
  }, []);

  const elapsedMin = Math.floor(elapsed / 60);
  const elapsedSec = elapsed % 60;
  const checkedIn = checkins.length;
  const totalStudents = classInfo.students;
  const progressPct = Math.min(100, Math.round((checkedIn / totalStudents) * 100));

  return (
    <div style={styles.kioskRoot}>
      {/* ── Header bar ── */}
      <header style={styles.header}>
        <div style={styles.headerLeft}>
          <div style={styles.liveIndicator}>
            <span className="pulse-dot" />
            <span>Đang điểm danh</span>
          </div>
          <span style={styles.headerDivider}>|</span>
          <span style={styles.headerClass}>{classInfo.id} — {classInfo.name}</span>
          <span style={styles.headerDivider}>|</span>
          <span style={styles.headerMeta}>Phòng {classInfo.room}</span>
        </div>
        <div style={styles.headerRight}>
          <span style={styles.timerDisplay}>
            ⏱ {String(elapsedMin).padStart(2, "0")}:{String(elapsedSec).padStart(2, "0")}
          </span>
          <span style={styles.headerMeta}>Bắt đầu: {formatTime(startTime)}</span>
          <button
            type="button"
            className="btn btn-danger"
            style={styles.stopBtn}
            onClick={() => setShowSummaryModal(true)}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <rect x="6" y="6" width="12" height="12" rx="2" />
            </svg>
            Dừng điểm danh
          </button>
        </div>
      </header>

      {/* ── Main content ── */}
      <div style={styles.mainContent}>
        {/* Camera section */}
        <div style={styles.cameraSection}>
          <div style={styles.cameraContainer}>
            {cameraError ? (
              <div style={styles.cameraError}>
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--danger)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M10.28 2.28L3.99 8.57c-.47.47-.73 1.1-.73 1.77V18c0 1.1.9 2 2 2h12c.67 0 1.3-.26 1.77-.73l6.29-6.29" />
                  <line x1="1" y1="1" x2="23" y2="23" />
                </svg>
                <p>{cameraError}</p>
              </div>
            ) : (
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                style={styles.video}
              />
            )}

            {/* ── Check-in overlay ── */}
            {overlay && (
              <div
                style={{
                  ...styles.overlay,
                  ...(overlay.success ? styles.overlaySuccess : styles.overlayFail),
                }}
                className="fade-in"
              >
                <div style={styles.overlayIcon}>
                  {overlay.success ? (
                    <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M20 6L9 17l-5-5" />
                    </svg>
                  ) : (
                    <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <line x1="18" y1="6" x2="6" y2="18" />
                      <line x1="6" y1="6" x2="18" y2="18" />
                    </svg>
                  )}
                </div>
                <div style={styles.overlayName}>{overlay.name}</div>
                <div style={styles.overlayMssv}>{overlay.mssv}</div>
                <div style={styles.overlayStatus}>
                  {overlay.success ? "Điểm danh thành công" : "Không nhận diện được"}
                </div>
              </div>
            )}

            {/* Camera instruction */}
            {!overlay && !cameraError && (
              <div style={{
                ...styles.cameraHint,
                ...(verifyingHint ? { background: "rgba(16, 185, 129, 0.85)", borderColor: "rgba(52, 211, 153, 0.6)" } : {})
              }}>
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
                {verifyingHint || "Nhìn vào camera để điểm danh"}
              </div>
            )}
          </div>

          {/* Stats bar below camera */}
          <div style={styles.statsBar}>
            <div style={styles.statItem}>
              <span style={styles.statValue}>{checkedIn}</span>
              <span style={styles.statLabel}>Đã điểm danh</span>
            </div>
            <div style={styles.statDivider} />
            <div style={styles.statItem}>
              <span style={styles.statValue}>{totalStudents - checkedIn}</span>
              <span style={styles.statLabel}>Chưa điểm danh</span>
            </div>
            <div style={styles.statDivider} />
            <div style={styles.statItem}>
              <span style={styles.statValue}>{progressPct}%</span>
              <span style={styles.statLabel}>Hoàn thành</span>
            </div>
            {/* Progress bar */}
            <div style={styles.progressTrack}>
              <div style={{ ...styles.progressFill, width: `${progressPct}%` }} />
            </div>
          </div>
        </div>

        {/* ── Check-in list panel ── */}
        <div style={styles.listPanel}>
          <div style={styles.listHeader}>
            <h3 style={styles.listTitle}>Danh sách điểm danh</h3>
            <span className="badge badge-success" style={{ fontSize: 12 }}>
              {checkedIn} / {totalStudents}
            </span>
          </div>

          <div style={styles.listScroll}>
            {checkedIn === 0 ? (
              <div style={styles.emptyState}>
                <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10" />
                  <path d="M12 6v6l4 2" />
                </svg>
                <p>Đang chờ sinh viên…</p>
              </div>
            ) : (
              checkins.map((c, i) => (
                <div key={c.mssv} className="fade-in" style={styles.listItem}>
                  <div style={styles.listItemLeft}>
                    <div style={styles.listItemIndex}>{i + 1}</div>
                    <div>
                      <div style={styles.listItemName}>{c.name}</div>
                      <div style={styles.listItemMssv}>{c.mssv}</div>
                    </div>
                  </div>
                  <div style={styles.listItemTime}>
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="var(--success)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M20 6L9 17l-5-5" />
                    </svg>
                    {formatTime(c.time)}
                  </div>
                </div>
              ))
            )}
            <div ref={listEndRef} />
          </div>
        </div>
      </div>

      {/* ── Footer ── */}
      <footer style={styles.footer}>
        <div style={styles.footerLeft}>
          {teacher.name} ({teacher.id})
        </div>
        <button
          type="button"
          style={styles.logoutLink}
          onClick={onLogout}
        >
          Đăng xuất
        </button>
      </footer>

      {/* ── Summary & Export Modal khi dừng điểm danh ── */}
      {showSummaryModal && (
        <div style={styles.modalBackdrop}>
          <div className="card fade-in" style={styles.modalCard}>
            <div style={styles.modalHeader}>
              <div style={styles.modalIconSuccess}>
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                  <polyline points="22 4 12 14.01 9 11.01" />
                </svg>
              </div>
              <h3 style={styles.modalTitle}>Kết thúc phiên điểm danh</h3>
              <p style={styles.modalSubtitle}>
                Lớp: <strong>{classInfo.id} — {classInfo.name}</strong>
              </p>
            </div>

            <div style={styles.modalBody}>
              <div style={styles.summaryGrid}>
                <div style={styles.summaryBox}>
                  <span style={styles.summaryLabel}>Có mặt</span>
                  <span style={{ ...styles.summaryValue, color: "var(--success)" }}>{checkedIn}</span>
                </div>
                <div style={styles.summaryBox}>
                  <span style={styles.summaryLabel}>Vắng mặt</span>
                  <span style={{ ...styles.summaryValue, color: "var(--danger)" }}>{Math.max(0, totalStudents - checkedIn)}</span>
                </div>
                <div style={styles.summaryBox}>
                  <span style={styles.summaryLabel}>Sĩ số lớp</span>
                  <span style={styles.summaryValue}>{totalStudents}</span>
                </div>
              </div>

              <p style={styles.modalPromptText}>
                Bạn có muốn xuất danh sách sinh viên đã điểm danh hôm nay ra file Excel (.csv) không?
              </p>
            </div>

            <div style={styles.modalFooter}>
              <button
                type="button"
                className="btn btn-secondary"
                style={styles.modalBtnCancel}
                onClick={() => {
                  setShowSummaryModal(false);
                  onEndSession();
                }}
              >
                Bỏ qua
              </button>

              <button
                type="button"
                className="btn btn-primary"
                style={styles.modalBtnExport}
                onClick={exportToExcel}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="7 10 12 15 17 10" />
                  <line x1="12" y1="15" x2="12" y2="3" />
                </svg>
                Xuất Excel (.csv)
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Styles ──────────────────────────────────────────────────
const styles = {
  kioskRoot: {
    display: "flex",
    flexDirection: "column",
    height: "100vh",
    overflow: "hidden",
    background: "var(--bg-primary)",
  },

  // ── Header ──
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "10px 24px",
    background: "rgba(15, 23, 42, 0.9)",
    backdropFilter: "blur(8px)",
    borderBottom: "1px solid var(--border)",
    flexShrink: 0,
    flexWrap: "wrap",
    gap: 8,
  },
  headerLeft: {
    display: "flex",
    alignItems: "center",
    gap: 12,
  },
  headerRight: {
    display: "flex",
    alignItems: "center",
    gap: 16,
  },
  liveIndicator: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    fontSize: 14,
    fontWeight: 600,
    color: "var(--success)",
  },
  headerDivider: {
    color: "var(--text-muted)",
    opacity: 0.4,
  },
  headerClass: {
    fontSize: 14,
    fontWeight: 600,
    color: "var(--text-primary)",
  },
  headerMeta: {
    fontSize: 13,
    color: "var(--text-muted)",
  },
  timerDisplay: {
    fontSize: 14,
    fontWeight: 700,
    fontFamily: "monospace",
    color: "var(--text-primary)",
    background: "var(--bg-input)",
    padding: "4px 10px",
    borderRadius: "var(--radius-sm)",
  },
  stopBtn: {
    padding: "8px 16px",
    fontSize: 13,
    marginLeft: 4,
  },

  // ── Main ──
  mainContent: {
    display: "flex",
    flex: 1,
    overflow: "hidden",
  },

  // ── Camera section ──
  cameraSection: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    minWidth: 0,
  },
  cameraContainer: {
    position: "relative",
    flex: 1,
    background: "#000",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    overflow: "hidden",
  },
  video: {
    width: "100%",
    height: "100%",
    objectFit: "cover",
    transform: "scaleX(-1)", // mirror for selfie-cam feel
  },
  cameraError: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 12,
    color: "var(--text-muted)",
    fontSize: 15,
    textAlign: "center",
    padding: 32,
  },

  // Camera hint
  cameraHint: {
    position: "absolute",
    bottom: 24,
    left: "50%",
    transform: "translateX(-50%)",
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: "10px 20px",
    background: "rgba(0, 0, 0, 0.6)",
    backdropFilter: "blur(8px)",
    borderRadius: 999,
    color: "rgba(255,255,255,0.85)",
    fontSize: 15,
    fontWeight: 500,
    whiteSpace: "nowrap",
  },

  // ── Check-in overlay on camera ──
  overlay: {
    position: "absolute",
    inset: 0,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    zIndex: 10,
  },
  overlaySuccess: {
    background: "rgba(0, 0, 0, 0.65)",
    color: "var(--success)",
  },
  overlayFail: {
    background: "rgba(0, 0, 0, 0.65)",
    color: "var(--danger)",
  },
  overlayIcon: {
    width: 88,
    height: 88,
    borderRadius: "50%",
    border: "3px solid currentColor",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 8,
  },
  overlayName: {
    fontSize: 32,
    fontWeight: 800,
    color: "white",
  },
  overlayMssv: {
    fontSize: 18,
    fontFamily: "monospace",
    color: "rgba(255,255,255,0.7)",
  },
  overlayStatus: {
    fontSize: 18,
    fontWeight: 600,
    marginTop: 4,
  },

  // ── Stats bar ──
  statsBar: {
    display: "flex",
    alignItems: "center",
    gap: 20,
    padding: "12px 24px",
    background: "var(--bg-secondary)",
    borderTop: "1px solid var(--border)",
    flexShrink: 0,
    flexWrap: "wrap",
  },
  statItem: {
    display: "flex",
    alignItems: "baseline",
    gap: 6,
  },
  statValue: {
    fontSize: 20,
    fontWeight: 700,
    fontFamily: "monospace",
  },
  statLabel: {
    fontSize: 12,
    color: "var(--text-muted)",
  },
  statDivider: {
    width: 1,
    height: 24,
    background: "var(--border)",
  },
  progressTrack: {
    flex: 1,
    minWidth: 80,
    height: 6,
    background: "var(--bg-input)",
    borderRadius: 99,
    overflow: "hidden",
  },
  progressFill: {
    height: "100%",
    background: "linear-gradient(90deg, var(--accent), var(--success))",
    borderRadius: 99,
    transition: "width 500ms ease",
  },

  // ── List panel (right side) ──
  listPanel: {
    width: 340,
    display: "flex",
    flexDirection: "column",
    background: "var(--bg-secondary)",
    borderLeft: "1px solid var(--border)",
    flexShrink: 0,
  },
  listHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "14px 20px",
    borderBottom: "1px solid var(--border)",
    flexShrink: 0,
  },
  listTitle: {
    fontSize: 15,
    fontWeight: 700,
    margin: 0,
  },
  listScroll: {
    flex: 1,
    overflowY: "auto",
    padding: "8px 12px",
  },
  emptyState: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 10,
    paddingTop: 60,
    color: "var(--text-muted)",
    fontSize: 14,
    textAlign: "center",
  },

  listItem: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "10px 12px",
    borderRadius: "var(--radius-sm)",
    marginBottom: 2,
    transition: "background 150ms ease",
  },
  listItemLeft: {
    display: "flex",
    alignItems: "center",
    gap: 10,
  },
  listItemIndex: {
    width: 28,
    height: 28,
    borderRadius: "50%",
    background: "var(--accent-glow)",
    color: "var(--accent-hover)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 12,
    fontWeight: 700,
    flexShrink: 0,
  },
  listItemName: {
    fontSize: 14,
    fontWeight: 600,
  },
  listItemMssv: {
    fontSize: 12,
    color: "var(--text-muted)",
    fontFamily: "monospace",
  },
  listItemTime: {
    display: "flex",
    alignItems: "center",
    gap: 4,
    fontSize: 12,
    color: "var(--success)",
    fontFamily: "monospace",
    fontWeight: 500,
    flexShrink: 0,
  },

  // ── Footer ──
  footer: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "8px 24px",
    background: "rgba(15, 23, 42, 0.9)",
    borderTop: "1px solid var(--border)",
    flexShrink: 0,
    minHeight: 44,
  },
  footerLeft: {
    fontSize: 13,
    color: "var(--text-muted)",
  },
  logoutLink: {
    background: "none",
    border: "none",
    color: "var(--text-muted)",
    cursor: "pointer",
    fontSize: 13,
    padding: "4px 8px",
    textDecoration: "underline",
    transition: "color 150ms ease",
  },

  // ── Modal kết thúc & xuất Excel ──
  modalBackdrop: {
    position: "fixed",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: "rgba(0, 0, 0, 0.75)",
    backdropFilter: "blur(4px)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    zIndex: 1000,
    padding: 16,
  },
  modalCard: {
    width: "100%",
    maxWidth: 440,
    background: "var(--bg-card)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius-lg, 16px)",
    padding: 24,
    boxShadow: "0 20px 40px rgba(0, 0, 0, 0.4)",
    textAlign: "center",
  },
  modalHeader: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    marginBottom: 18,
  },
  modalIconSuccess: {
    width: 56,
    height: 56,
    borderRadius: "50%",
    background: "rgba(16, 185, 129, 0.15)",
    color: "var(--success)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 12,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: 700,
    color: "var(--text-primary)",
    margin: "0 0 4px 0",
  },
  modalSubtitle: {
    fontSize: 14,
    color: "var(--text-muted)",
    margin: 0,
  },
  modalBody: {
    marginBottom: 24,
  },
  summaryGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(3, 1fr)",
    gap: 8,
    background: "var(--bg-input)",
    padding: "12px 8px",
    borderRadius: "var(--radius-md, 10px)",
    marginBottom: 16,
  },
  summaryBox: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
  },
  summaryLabel: {
    fontSize: 11,
    color: "var(--text-muted)",
    marginBottom: 4,
    textTransform: "uppercase",
  },
  summaryValue: {
    fontSize: 18,
    fontWeight: 700,
    color: "var(--text-primary)",
  },
  modalPromptText: {
    fontSize: 14,
    color: "var(--text-secondary)",
    lineHeight: 1.5,
    margin: 0,
  },
  modalFooter: {
    display: "flex",
    gap: 12,
    justifyContent: "center",
  },
  modalBtnCancel: {
    flex: 1,
    padding: "10px 16px",
    fontWeight: 600,
  },
  modalBtnExport: {
    flex: 1.2,
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    padding: "10px 16px",
    fontWeight: 600,
    background: "var(--accent)",
  },
};
