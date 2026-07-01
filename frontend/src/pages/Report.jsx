import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import client from '../api/client';
import Footer from '../components/Footer';

export default function Report() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [report, setReport] = useState(null);
  const [status, setStatus] = useState('queued');
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    const poll = async () => {
      const { data } = await client.get(`/reports/${sessionId}/status`);
      setStatus(data.status);
      if (data.status === 'ready') {
        setReport(data.report);
      } else if (data.status !== 'failed') {
        setTimeout(poll, 3000);
      }
    };
    poll();
  }, [sessionId]);

  async function download() {
    setDownloading(true);
    try {
      const { data } = await client.get(`/reports/${sessionId}/download`);
      window.open(data.download_url, '_blank');
    } catch {
      alert('PDF not available yet.');
    } finally {
      setDownloading(false);
    }
  }

  if (status === 'queued' || status === 'generating') {
    return (
      <div style={styles.center}>
        <div style={styles.generating}>
          <div style={styles.spinner} />
          <h2>Generating your report...</h2>
          <p>This usually takes 30–60 seconds. Please wait.</p>
        </div>
      </div>
    );
  }

  if (status === 'failed') {
    return (
      <div style={styles.center}>
        <div style={styles.card}>
          <h2 style={{ color: '#e53935' }}>Report Generation Failed</h2>
          <p>Something went wrong. Please try again or contact support.</p>
          <button style={styles.btn} onClick={() => navigate('/dashboard')}>Back to Dashboard</button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ ...styles.container, display: 'flex', flexDirection: 'column' }}>
      <header style={styles.header}>
        <span style={styles.logo}>MindScope</span>
        <button style={styles.downloadBtn} onClick={download} disabled={downloading}>
          {downloading ? 'Preparing...' : '⬇ Download PDF'}
        </button>
      </header>

      <main role="main" style={styles.main}>
        {report && (
          <>
            <Section title="Snapshot" content={report.snapshot} color="#4285f4" />
            <Section title="Your Strengths" content={report.strengths} color="#4caf50" />
            <Section title="Friction Points" content={report.friction_points} color="#ff9800" />
            <Section title="Career Directions" items={report.career_directions} color="#9c27b0" />
            <Section title="Your Next Steps" items={report.next_steps} color="#00bcd4" />
          </>
        )}

        <div style={styles.footer}>
          <p>This is a strengths and career-fit tool, not a clinical diagnostic assessment.</p>
          <button style={styles.dashBtn} onClick={() => navigate('/dashboard')}>Back to Dashboard</button>
        </div>
      </main>
      <Footer />
    </div>
  );
}

function Section({ title, content, items, color }) {
  return (
    <div style={{ ...styles.section, borderLeft: `4px solid ${color}` }}>
      <h3 style={{ color, marginTop: 0 }}>{title}</h3>
      {content && <p style={styles.text}>{content}</p>}
      {items && (
        <ul style={styles.list}>
          {items.map((item, i) => <li key={i} style={styles.listItem}>{item}</li>)}
        </ul>
      )}
    </div>
  );
}

const styles = {
  container: { minHeight: '100vh', background: '#f5f5f5' },
  center: { display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh' },
  generating: { textAlign: 'center', padding: '48px' },
  spinner: { width: 48, height: 48, border: '4px solid #ddd', borderTopColor: '#4285f4', borderRadius: '50%', animation: 'spin 1s linear infinite', margin: '0 auto 24px' },
  header: { background: '#1a1a2e', color: '#fff', padding: '16px 32px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', position: 'sticky', top: 0 },
  logo: { fontWeight: 700, fontSize: '1.1rem' },
  downloadBtn: { background: '#4caf50', color: '#fff', border: 'none', padding: '10px 20px', borderRadius: '6px', cursor: 'pointer' },
  main: { maxWidth: '800px', margin: '0 auto', padding: '32px 16px' },
  section: { background: '#fff', borderRadius: '10px', padding: '24px 24px 24px 20px', marginBottom: '16px', boxShadow: '0 2px 8px rgba(0,0,0,0.06)', overflow: 'hidden', wordBreak: 'break-word' },
  text: { lineHeight: 1.7, color: '#333' },
  list: { paddingLeft: '20px', margin: 0 },
  listItem: { marginBottom: '10px', lineHeight: 1.6, color: '#333' },
  footer: { textAlign: 'center', padding: '24px 0', color: '#999', fontSize: '0.85rem' },
  dashBtn: { background: '#1a1a2e', color: '#fff', border: 'none', padding: '10px 24px', borderRadius: '6px', cursor: 'pointer', marginTop: '12px' },
  card: { background: '#fff', borderRadius: '12px', padding: '40px', textAlign: 'center', maxWidth: '400px' },
  btn: { background: '#4285f4', color: '#fff', border: 'none', padding: '12px 24px', borderRadius: '8px', cursor: 'pointer', marginTop: '16px' },
};
