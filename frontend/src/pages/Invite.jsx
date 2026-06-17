import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import client from '../api/client';

export default function Invite() {
  const { code } = useParams();
  const navigate = useNavigate();
  const [org, setOrg] = useState(null);
  const [error, setError] = useState('');
  const [activating, setActivating] = useState(false);

  useEffect(() => {
    client.get('/b2b/validate-invite', { params: { code } })
      .then(({ data }) => setOrg(data))
      .catch((err) => setError(err.response?.data?.detail || 'Invalid or expired invite link.'));
  }, [code]);

  async function activate() {
    const token = sessionStorage.getItem('access_token');
    if (!token) {
      sessionStorage.setItem('pending_invite', code);
      navigate('/login');
      return;
    }
    setActivating(true);
    try {
      await client.post('/b2b/activate-invite', null, { params: { code } });
      // Start a new B2B session
      const { data } = await client.post('/sessions', { context_of_origin: org.context_of_origin });
      navigate(`/intake/${data.id}`);
    } catch (err) {
      setError(err.response?.data?.detail || 'Activation failed.');
    } finally {
      setActivating(false);
    }
  }

  if (error) {
    return (
      <div style={styles.center}>
        <div style={styles.card}>
          <h2 style={{ color: '#e53935' }}>Invite Error</h2>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  if (!org) return <div style={styles.center}>Validating invite...</div>;

  return (
    <div style={styles.center}>
      <div style={styles.card}>
        <h1 style={styles.logo}>MindScope</h1>
        <div style={styles.orgBadge}>{org.org_name}</div>
        <h2>You've been invited!</h2>
        <p style={styles.sub}>
          {org.org_name} has invited you to take a psychometric assessment.
          {org.licenses_remaining} place{org.licenses_remaining !== 1 ? 's' : ''} remaining.
        </p>
        <button style={styles.btn} onClick={activate} disabled={activating}>
          {activating ? 'Activating...' : 'Join with Google →'}
        </button>
        <p style={styles.disclaimer}>No payment required — your organisation has pre-paid.</p>
      </div>
    </div>
  );
}

const styles = {
  center: { minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f5f5f5' },
  card: { background: '#fff', borderRadius: '12px', padding: '48px', textAlign: 'center', maxWidth: '440px', width: '100%', boxShadow: '0 4px 24px rgba(0,0,0,0.1)' },
  logo: { margin: '0 0 16px', color: '#1a1a2e' },
  orgBadge: { display: 'inline-block', background: '#e8f0fe', color: '#1a73e8', padding: '6px 16px', borderRadius: '20px', fontSize: '0.9rem', marginBottom: '16px' },
  sub: { color: '#555', marginBottom: '28px', lineHeight: 1.6 },
  btn: { background: '#4285f4', color: '#fff', border: 'none', padding: '14px 32px', borderRadius: '8px', fontSize: '1rem', cursor: 'pointer', width: '100%' },
  disclaimer: { color: '#999', fontSize: '0.8rem', marginTop: '16px' },
};
