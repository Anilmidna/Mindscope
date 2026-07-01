import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import client from '../api/client';
import { clearToken } from '../auth';
import Footer from '../components/Footer';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorBanner from '../components/ErrorBanner';

const STATUS_COLORS = {
  started:       '#ff9800',
  intake_done:   '#ff9800',
  riasec_done:   '#2196f3',
  bigfive_done:  '#2196f3',
  aptitude_done: '#2196f3',
  complete:      '#9c27b0',
  scored:        '#9c27b0',
  report_ready:  '#4caf50',
  failed:        '#e53935',
};

const STATUS_LABELS = {
  started:       'Started',
  intake_done:   'Intake done',
  riasec_done:   'In progress',
  bigfive_done:  'In progress',
  aptitude_done: 'In progress',
  complete:      'Scoring...',
  scored:        'Generating report...',
  report_ready:  'Report ready',
  failed:        'Failed',
};

const REPORT_STATUSES = new Set(['complete', 'scored', 'report_ready']);
const IN_PROGRESS_STATUSES = new Set(['started', 'intake_done', 'riasec_done', 'bigfive_done', 'aptitude_done']);

export default function Dashboard() {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [starting, setStarting] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    client.get('/sessions')
      .then(({ data }) => setSessions(data))
      .catch(() => setError('Could not load sessions. Please refresh.'))
      .finally(() => setLoading(false));
  }, []);

  async function startNew() {
    setStarting(true);
    setError('');
    try {
      const { data } = await client.post('/sessions', { context_of_origin: 'standalone-public' });
      navigate(`/intake/${data.id}`);
    } catch {
      setError('Could not start a new assessment. Please try again.');
      setStarting(false);
    }
  }

  function resume(session) {
    if (REPORT_STATUSES.has(session.status)) {
      navigate(`/report/${session.id}`);
    } else {
      navigate(`/assessment/${session.id}`);
    }
  }

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <h1 style={styles.logo}>MindScope</h1>
        <button style={styles.logoutBtn} onClick={() => { client.post('/auth/logout', {}).catch(() => {}); clearToken(); navigate('/login'); }}>
          Logout
        </button>
      </header>

      <main role="main" style={styles.main}>
        <div style={styles.topRow}>
          <h2>Your Assessments</h2>
          <button style={styles.startBtn} onClick={startNew} disabled={starting}>
            {starting ? 'Starting...' : '+ Start New Assessment'}
          </button>
        </div>

        {error && <ErrorBanner message={error} onRetry={() => window.location.reload()} />}
        {loading && <LoadingSpinner message="Loading your sessions..." />}

        {!loading && sessions.length === 0 && (
          <div style={styles.empty}>
            <p>No assessments yet. Start your first one!</p>
          </div>
        )}

        <div style={styles.grid}>
          {sessions.map((s) => (
            <div key={s.id} style={styles.card}>
              <div style={{ ...styles.badge, background: STATUS_COLORS[s.status] || '#999' }}>
                {STATUS_LABELS[s.status] || s.status}
              </div>
              <p style={styles.date}>{new Date(s.started_at).toLocaleDateString()}</p>
              <p style={styles.context}>{s.context_of_origin}</p>
              {s.status !== 'failed' && (
                <button style={styles.resumeBtn} onClick={() => resume(s)}>
                  {REPORT_STATUSES.has(s.status) ? 'View Report' : 'Resume'}
                </button>
              )}
              {s.status === 'report_ready' && (
                <p style={styles.emailNote}>Report sent to your email</p>
              )}
            </div>
          ))}
        </div>
      </main>
      <Footer />
    </div>
  );
}

const styles = {
  container: { minHeight: '100vh', background: '#f5f5f5' },
  header: { background: '#1a1a2e', color: '#fff', padding: '16px 32px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  logo: { margin: 0, fontSize: '1.5rem' },
  logoutBtn: { background: 'transparent', color: '#fff', border: '1px solid rgba(255,255,255,0.4)', padding: '8px 16px', borderRadius: '6px', cursor: 'pointer' },
  main: { maxWidth: '900px', margin: '0 auto', padding: '32px 16px' },
  topRow: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', flexWrap: 'wrap', gap: '12px' },
  startBtn: { background: '#4285f4', color: '#fff', border: 'none', padding: '12px 24px', borderRadius: '8px', cursor: 'pointer', fontSize: '1rem', whiteSpace: 'nowrap' },
  empty: { textAlign: 'center', color: '#999', padding: '48px' },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '16px', width: '100%', maxWidth: '100%' },
  card: { background: '#fff', borderRadius: '10px', padding: '20px', boxShadow: '0 2px 8px rgba(0,0,0,0.08)', minWidth: 0 },
  badge: { display: 'inline-block', color: '#fff', padding: '4px 10px', borderRadius: '12px', fontSize: '0.75rem', marginBottom: '8px' },
  date: { color: '#999', fontSize: '0.85rem', margin: '4px 0' },
  context: { color: '#555', fontSize: '0.9rem', margin: '4px 0 12px' },
  resumeBtn: { background: '#1a1a2e', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: '6px', cursor: 'pointer', width: '100%' },
  emailNote: { color: '#4caf50', fontSize: '0.8rem', marginTop: '6px', textAlign: 'center' },
};
