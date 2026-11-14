import { useState, useEffect } from "react";

export default function StudentManageModal({ teacher, onClose, onRefresh }) {
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deletingMssv, setDeletingMssv] = useState(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [message, setMessage] = useState(null);

  useEffect(() => {
    fetchStudents();
  }, []);

  async function fetchStudents() {
    setLoading(true);
    try {
      const res = await fetch("http://127.0.0.1:8000/api/students", {
        headers: {
          Authorization: `Bearer ${teacher.token}`,
        },
      });
      if (res.ok) {
        const data = await res.json();
        setStudents(data);
      }
    } catch (err) {
      console.error(err);
      setMessage({ type: "error", text: "Không thể tải danh sách sinh viên." });
    } finally {
      setLoading(false);
    }
  }

  async function handleDeleteFace(mssv, name) {
    if (!window.confirm(`Bạn có chắc chắn muốn xóa dữ liệu khuôn mặt của sinh viên:\n${name} (MSSV: ${mssv})?`)) {
      return;
    }

    setDeletingMssv(mssv);
    setMessage(null);

    try {
      const res = await fetch(`http://127.0.0.1:8000/api/students/${mssv}/face`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${teacher.token}`,
        },
      });

      const data = await res.json();
      if (res.ok) {
        setMessage({ type: "success", text: data.message || `Đã xóa khuôn mặt của ${name}!` });
        // Cập nhật lại UI cục bộ
        setStudents((prev) =>
          prev.map((s) => (s.mssv === mssv ? { ...s, enrolled: false, embeddings_count: 0 } : s))
        );
        if (onRefresh) onRefresh();
      } else {
        setMessage({ type: "error", text: data.detail || "Xóa khuôn mặt thất bại." });
      }
    } catch (err) {
      console.error(err);
      setMessage({ type: "error", text: "Lỗi kết nối máy chủ khi xóa khuôn mặt." });
    } finally {
      setDeletingMssv(null);
    }
  }

  const filteredStudents = students.filter(
    (s) =>
      s.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      s.mssv.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div style={modalStyles.backdrop}>
      <div className="card fade-in" style={modalStyles.modal}>
        {/* Header */}
        <div style={modalStyles.header}>
          <div>
            <h2 style={modalStyles.title}>👥 Quản lý & Xóa dữ liệu khuôn mặt</h2>
            <p style={modalStyles.subtitle}>Danh sách sinh viên và trạng thái đăng ký sinh trắc học</p>
          </div>
          <button type="button" onClick={onClose} style={modalStyles.closeBtn}>✕</button>
        </div>

        {/* Search bar */}
        <div style={{ marginBottom: 16 }}>
          <input
            type="text"
            className="input"
            placeholder="🔍 Tìm theo tên hoặc MSSV..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        {/* Message Alert */}
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

        {/* Student List */}
        <div style={modalStyles.listWrapper}>
          {loading ? (
            <div style={modalStyles.emptyText}>Đang tải dữ liệu...</div>
          ) : filteredStudents.length === 0 ? (
            <div style={modalStyles.emptyText}>Không tìm thấy sinh viên nào.</div>
          ) : (
            <div style={modalStyles.list}>
              {filteredStudents.map((s) => (
                <div key={s.mssv} style={modalStyles.studentItem}>
                  <div style={modalStyles.studentInfo}>
                    <div style={modalStyles.avatar}>{s.name.charAt(0)}</div>
                    <div>
                      <div style={modalStyles.studentName}>{s.name}</div>
                      <div style={modalStyles.studentMssv}>MSSV: {s.mssv}</div>
                    </div>
                  </div>

                  <div style={modalStyles.studentActions}>
                    {s.enrolled ? (
                      <>
                        <span className="badge badge-success" style={{ fontSize: 12 }}>
                          ✓ Đã có mặt
                        </span>
                        <button
                          type="button"
                          className="btn btn-ghost"
                          style={modalStyles.deleteBtn}
                          disabled={deletingMssv === s.mssv}
                          onClick={() => handleDeleteFace(s.mssv, s.name)}
                          title="Xóa mẫu khuôn mặt"
                        >
                          {deletingMssv === s.mssv ? "Đang xóa..." : "🗑️ Xóa mặt"}
                        </button>
                      </>
                    ) : (
                      <span className="badge badge-muted" style={{ fontSize: 12, opacity: 0.6 }}>
                        Chưa đăng ký
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={modalStyles.footer}>
          <div style={{ fontSize: 13, color: "var(--text-muted)" }}>
            Tổng số: <strong>{filteredStudents.length}</strong> sinh viên ({filteredStudents.filter((s) => s.enrolled).length} đã có mẫu khuôn mặt)
          </div>
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Đóng
          </button>
        </div>
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
    maxWidth: 640,
    maxHeight: "88vh",
    display: "flex",
    flexDirection: "column",
    padding: 24,
    borderRadius: "var(--radius-lg, 16px)",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: 16,
  },
  title: {
    fontSize: 18,
    fontWeight: 700,
    margin: 0,
  },
  subtitle: {
    fontSize: 13,
    color: "var(--text-muted)",
    margin: "4px 0 0 0",
  },
  closeBtn: {
    background: "transparent",
    border: "none",
    color: "var(--text-muted)",
    fontSize: 20,
    cursor: "pointer",
    padding: "4px 8px",
  },
  listWrapper: {
    flex: 1,
    overflowY: "auto",
    minHeight: 280,
    maxHeight: 380,
    border: "1px solid var(--border)",
    borderRadius: 8,
    padding: 8,
    backgroundColor: "rgba(0,0,0,0.15)",
  },
  list: {
    display: "flex",
    flexDirection: "column",
    gap: 8,
  },
  studentItem: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "10px 14px",
    borderRadius: 8,
    backgroundColor: "var(--bg-secondary, rgba(255,255,255,0.03))",
    border: "1px solid rgba(255,255,255,0.05)",
  },
  studentInfo: {
    display: "flex",
    alignItems: "center",
    gap: 12,
  },
  avatar: {
    width: 36,
    height: 36,
    borderRadius: "50%",
    backgroundColor: "var(--primary-muted, rgba(99, 102, 241, 0.2))",
    color: "var(--primary, #6366f1)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontWeight: 700,
    fontSize: 14,
  },
  studentName: {
    fontSize: 14,
    fontWeight: 600,
    color: "var(--text)",
  },
  studentMssv: {
    fontSize: 12,
    color: "var(--text-muted)",
  },
  studentActions: {
    display: "flex",
    alignItems: "center",
    gap: 10,
  },
  deleteBtn: {
    color: "#f87171",
    fontSize: 12,
    padding: "4px 10px",
    border: "1px solid rgba(248, 113, 113, 0.3)",
    borderRadius: 6,
    background: "rgba(239, 68, 68, 0.08)",
  },
  emptyText: {
    textAlign: "center",
    padding: "40px 0",
    color: "var(--text-muted)",
    fontSize: 14,
  },
  alert: {
    padding: "10px 14px",
    borderRadius: 8,
    fontSize: 13,
    borderWidth: 1,
    borderStyle: "solid",
    marginBottom: 14,
  },
  footer: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginTop: 16,
    paddingTop: 12,
    borderTop: "1px solid var(--border)",
  },
};
