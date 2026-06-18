import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Intake from './pages/Intake';
import Assessment from './pages/Assessment';
import Report from './pages/Report';
import Invite from './pages/Invite';
import NotFound from './pages/NotFound';

function ProtectedRoute({ children }) {
  const token = sessionStorage.getItem('access_token');
  return token ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/invite/:code" element={<Invite />} />
        <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route path="/intake/:sessionId" element={<ProtectedRoute><Intake /></ProtectedRoute>} />
        <Route path="/assessment/:sessionId" element={<ProtectedRoute><Assessment /></ProtectedRoute>} />
        <Route path="/report/:sessionId" element={<ProtectedRoute><Report /></ProtectedRoute>} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  );
}
