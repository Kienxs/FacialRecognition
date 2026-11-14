import { useState } from "react";
import EnrollModal from "./EnrollModal.jsx";
import StudentManageModal from "./StudentManageModal.jsx";

// ── Mock data ──────────────────────────────────────────────
const MOCK_CLASSES = [
  { id: "CS101", name: "Nhập môn CNTT", schedule: "Thứ 2 — 7:30", room: "A2-301", students: 42 },
  { id: "CS201", name: "Cấu trúc dữ liệu", schedule: "Thứ 4 — 9:00", room: "B1-205", students: 38 },
  { id: "CS305", name: "Trí tuệ nhân tạo", schedule: "Thứ 6 — 13:30", room: "C3-102", students: 35 },
];

// ── Component ──────────────────────────────────────────────
export default function DashboardPage({ teacher, onLogout, onStartSession }) {
  const [confirmClass, setConfirmClass] = useState(null);
  const [showEnroll, setShowEnroll] = useState(false);
  const [showManage, setShowManage] = useState(false);

  function handleCardClick(cls) {
    setConfirmClass(cls);
  }

  function handleConfirm() {
    if (confirmClass) onStartSession(confirmClass);
  }

  return (
    <div className="page-bg" style={styles.page}>
      <div className="fade-in" style={styles.container}>
        {/* Top bar */}
        <header style={styles.topBar}>
          <div style={styles.teacherInfo}>
            <div style={styles.avatar}>
              {teacher.name.charAt(0)}
            </div>
            <div>
              <div style={styles.teacherName}>{teacher.name}</div>
              <div style={styles.teacherId}>{teacher.id}</div>
            </div>
          </div>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <button
              type="button"
              className="btn btn-ghost"
              style={{ padding: "8px 14px", fontSize: 13, border: "1px solid var(--border)" }}
              onClick={() => setShowManage(true)}
            >
              👥 Quản lý & Xóa mặt
            </button>
            <button
              type="button"
              className="btn btn-primary"
              style={{ padding: "8px 14px", fontSize: 13 }}
              onClick={() => setShowEnroll(true)}
            >
              📸 Đăng ký khuôn mặt mới
            </button>
            <button type="button" className="btn btn-ghost" onClick={onLogout}>
              Đăng xuất
            </button>
          </div>
        </header>

        {showEnroll && (
          <EnrollModal
            teacher={teacher}
            onClose={() => setShowEnroll(false)}
          />
        )}

        {showManage && (
          <StudentManageModal
            teacher={teacher}
            onClose={() => setShowManage(false)}
          />
        )}

        {/* Title */}
        <div style={styles.sectionHeader}>
          <h1 style={styles.pageTitle}>Chọn lớp điểm danh</h1>
          <p style={styles.pageSubtitle}>Chọn lớp để mở camera điểm danh tại cửa phòng</p>
        </div>

        {/* Class grid */}
        <div style={styles.classGrid}>
          {MOCK_CLASSES.map((cls) => (
            <button
              key={cls.id}
              type="button"
              className="card"
              style={{
                ...styles.classCard,
                ...(confirmClass?.id === cls.id ? styles.classCardSelected : {}),
              }}
              onClick={() => handleCardClick(cls)}
            >
              <div style={styles.classCardTop}>
                <span className="badge badge-success" style={{ fontSize: 12 }}>
                  {cls.id}
                </span>
                <span style={styles.studentCount}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
                    <circle cx="9" cy="7" r="4" />
                    <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
                    <path d="M16 3.13a4 4 0 0 1 0 7.75" />
                  </svg>
                  {cls.students} SV
                </span>
              </div>
              <h3 style={styles.className}>{cls.name}</h3>
              <div style={styles.classMeta}>
                <span>📅 {cls.schedule}</span>
              </div>
              <div style={styles.classMeta}>
                <span>📍 Phòng {cls.room}</span>
              </div>
            </button>
          ))}
        </div>

        {/* Confirm button */}
        {confirmClass && (
          <div className="fade-in" style={styles.confirmBar}>
            <div style={styles.confirmText}>
              Mở điểm danh cho <strong>{confirmClass.name}</strong> — Phòng {confirmClass.room}?
            </div>
            <div style={styles.confirmActions}>
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => setConfirmClass(null)}
              >
                Huỷ
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleConfirm}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polygon points="5 3 19 12 5 21 5 3" />
                </svg>
                Bắt đầu
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Styles ──────────────────────────────────────────────────
const styles = {
  page: {
    display: "flex",
    justifyContent: "center",
    padding: "24px 16px",
  },
  container: {
    width: "100%",
    maxWidth: 800,
    display: "flex",
    flexDirection: "column",
    gap: 24,
  },
  topBar: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  teacherInfo: {
    display: "flex",
    alignItems: "center",
    gap: 12,
  },
  avatar: {
    width: 42,
    height: 42,
    borderRadius: "50%",
    backgroundColor: "var(--primary-muted)",
    color: "var(--primary)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontWeight: 700,
    fontSize: 16,
  },
  teacherName: {
    fontSize: 15,
    fontWeight: 600,
  },
  teacherId: {
    fontSize: 12,
    color: "var(--text-muted)",
  },
  sectionHeader: {
    display: "flex",
    flexDirection: "column",
    gap: 4,
  },
  pageTitle: {
    fontSize: 22,
    fontWeight: 700,
    margin: 0,
  },
  pageSubtitle: {
    fontSize: 14,
    color: "var(--text-secondary)",
    margin: 0,
  },
  classGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(230px, 1fr))",
    gap: 16,
  },
  classCard: {
    cursor: "pointer",
    textAlign: "left",
    display: "flex",
    flexDirection: "column",
    gap: 10,
    padding: 18,
    transition: "border-color 0.15s, transform 0.15s",
  },
  classCardSelected: {
    borderColor: "var(--primary)",
    boxShadow: "0 0 0 1px var(--primary)",
  },
  classCardTop: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  studentCount: {
    display: "flex",
    alignItems: "center",
    gap: 4,
    fontSize: 12,
    color: "var(--text-muted)",
  },
  className: {
    fontSize: 16,
    fontWeight: 600,
    margin: 0,
  },
  classMeta: {
    fontSize: 12,
    color: "var(--text-secondary)",
  },
  confirmBar: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    backgroundColor: "var(--card-bg)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius-md)",
    padding: "14px 20px",
  },
  confirmText: {
    fontSize: 14,
  },
  confirmActions: {
    display: "flex",
    gap: 10,
  },
};
