import { useState } from "react";
import LoginPage from "./LoginPage.jsx";
import DashboardPage from "./DashboardPage.jsx";
import KioskPage from "./KioskPage.jsx";

const AUTH_KEY = "checkin-teacher";

function readSavedTeacher() {
  try {
    const raw = sessionStorage.getItem(AUTH_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function App() {
  const [teacher, setTeacher] = useState(readSavedTeacher);
  const [activeClass, setActiveClass] = useState(null); // class currently in kiosk mode

  function handleLogin(teacherData) {
    sessionStorage.setItem(AUTH_KEY, JSON.stringify(teacherData));
    setTeacher(teacherData);
  }

  function handleLogout() {
    sessionStorage.removeItem(AUTH_KEY);
    setTeacher(null);
    setActiveClass(null);
  }

  function handleStartSession(cls) {
    setActiveClass(cls);
  }

  function handleEndSession() {
    setActiveClass(null);
  }

  // 1. Not logged in → Login
  if (!teacher) {
    return <LoginPage onLogin={handleLogin} />;
  }

  // 2. Logged in but no active class → Class selection
  if (!activeClass) {
    return (
      <DashboardPage
        teacher={teacher}
        onLogout={handleLogout}
        onStartSession={handleStartSession}
      />
    );
  }

  // 3. Active session → Kiosk mode
  return (
    <KioskPage
      teacher={teacher}
      classInfo={activeClass}
      onEndSession={handleEndSession}
      onLogout={handleLogout}
    />
  );
}

export default App;
