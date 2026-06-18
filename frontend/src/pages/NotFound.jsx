import { useNavigate } from 'react-router-dom';

export default function NotFound() {
  const navigate = useNavigate();
  return (
    <div style={styles.center}>
      <div style={styles.card}>
        <h1 style={styles.code}>404</h1>
        <h2 style={styles.title}>Page not found</h2>
        <p style={styles.sub}>The page you're looking for doesn't exist or has been moved.</p>
        <button style={styles.btn} onClick={() => navigate('/dashboard')}>Go to Dashboard</button>
      </div>
    </div>
  );
}

const styles = {
  center: { minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f5f5f5' },
  card: { background: '#fff', borderRadius: '12px', padding: '48px', textAlign: 'center', maxWidth: '400px', width: '100%', boxShadow: '0 4px 24px rgba(0,0,0,0.1)' },
  code: { fontSize: '4rem', fontWeight: 700, color: '#ddd', margin: '0 0 8px' },
  title: { margin: '0 0 12px', color: '#1a1a2e' },
  sub: { color: '#666', marginBottom: '28px' },
  btn: { background: '#4285f4', color: '#fff', border: 'none', padding: '12px 28px', borderRadius: '8px', fontSize: '1rem', cursor: 'pointer' },
};
