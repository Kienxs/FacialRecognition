import { useState } from "react";

export default function LoginPage({ onLogin }) {
  const [teacherId, setTeacherId] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSubmitting(true);

    // Gửi dữ liệu đăng nhập dưới dạng form-urlencoded theo chuẩn FastAPI
    const formData = new URLSearchParams();
    formData.append("username", teacherId.trim().toUpperCase());
    formData.append("password", password);

    try {
      const response = await fetch("http://127.0.0.1:8000/api/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: formData,
      });

      const data = await response.json();

      if (response.ok) {
        // Lưu thông tin và token khi thành công
        onLogin({ 
          id: teacherId.trim().toUpperCase(), 
          name: "Giảng viên", 
          token: data.access_token 
        });
      } else {
        setError(data.detail || "Sai mã giảng viên hoặc mật khẩu.");
      }
    } catch (err) {
      setError("Không thể kết nối đến máy chủ Backend.");
      console.error(err);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="page-bg" style={styles.page}>
      <form onSubmit={handleSubmit} className="card fade-in" style={styles.card}>
        {/* Header */}
        <div style={styles.header}>
          <div style={styles.iconCircle}>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
          </div>
          <h1 style={styles.title}>Đăng nhập Giảng viên</h1>
          <p style={styles.subtitle}>Hệ thống điểm danh thông minh</p>
        </div>

        {/* Demo hint */}
        <div style={styles.hint}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
            <circle cx="12" cy="12" r="10" />
            <path d="M12 16v-4" />
            <path d="M12 8h.01" />
          </svg>
          <span>Lưu ý: Cần Insert một tài khoản vào SQLite trước để test</span>
        </div>

        {/* Fields */}
        <label className="label">
          Mã giảng viên
          <input
            type="text"
            className="input"
            value={teacherId}
            onChange={(e) => setTeacherId(e.target.value)}
            placeholder="VD: GV001"
            autoComplete="username"
            required
          />
        </label>

        <label className="label">
          Mật khẩu
          <input
            type="password"
            className="input"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Nhập mật khẩu"
            autoComplete="current-password"
            required
          />
        </label>

        {/* Error */}
        {error && (
          <div role="alert" className="alert alert-error">
            {error}
          </div>
        )}

        {/* Submit */}
        <button
          type="submit"
          disabled={submitting}
          className="btn btn-primary"
          style={styles.submitBtn}
        >
          {submitting ? (
            <>
              <span className="spinner" />
              Đang đăng nhập…
            </>
          ) : (
            "Đăng nhập"
          )}
        </button>
      </form>
    </div>
  );
}

const styles = {
  page: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: 24,
  },
  card: {
    width: "100%",
    maxWidth: 420,
    display: "flex",
    flexDirection: "column",
    gap: 20,
    padding: "40px 32px",
  },
  header: {
    textAlign: "center",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 8,
  },
  iconCircle: {
    width: 56,
    height: 56,
    borderRadius: "50%",
    background: "linear-gradient(135deg, var(--accent), #8b5cf6)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    color: "white",
    marginBottom: 4,
    boxShadow: "0 0 24px var(--accent-glow)",
  },
  title: {
    fontSize: 24,
    fontWeight: 700,
    letterSpacing: "-0.02em",
  },
  subtitle: {
    fontSize: 14,
    color: "var(--text-muted)",
    margin: 0,
  },
  hint: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    padding: "10px 14px",
    fontSize: 13,
    color: "var(--text-secondary)",
    background: "rgba(99, 102, 241, 0.08)",
    borderRadius: "var(--radius-sm)",
    border: "1px solid rgba(99, 102, 241, 0.15)",
  },
  submitBtn: {
    width: "100%",
    padding: "14px 24px",
    fontSize: 16,
    marginTop: 4,
  },
};