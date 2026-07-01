import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { getToken } from './auth';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Intake from './pages/Intake';
import Checkout from './pages/Checkout';
import Assessment from './pages/Assessment';
import Report from './pages/Report';
import Invite from './pages/Invite';
import NotFound from './pages/NotFound';
import Privacy from './pages/Privacy';
import Terms from './pages/Terms';
import Refund from './pages/Refund';
import Contact from './pages/Contact';

function ProtectedRoute({ children }) {
  const token = getToken();
  return token ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/invite/:code" element={<Invite />} />
        <Route path="/privacy" element={<Privacy />} />
        <Route path="/terms" element={<Terms />} />
        <Route path="/refund" element={<Refund />} />
        <Route path="/contact" element={<Contact />} />
        <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route path="/intake/:sessionId" element={<ProtectedRoute><Intake /></ProtectedRoute>} />
        <Route path="/checkout/:sessionId" element={<ProtectedRoute><Checkout /></ProtectedRoute>} />
        <Route path="/assessment/:sessionId" element={<ProtectedRoute><Assessment /></ProtectedRoute>} />
        <Route path="/report/:sessionId" element={<ProtectedRoute><Report /></ProtectedRoute>} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  );
}
