import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import client from '../api/client';
import { setToken } from '../auth';
import Footer from '../components/Footer';

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;
const REDIRECT_URI = import.meta.env.VITE_REDIRECT_URI || 'http://localhost:5173/login';

function generateCodeVerifier() {
  const array = new Uint8Array(32);
  crypto.getRandomValues(array);
  return btoa(String.fromCharCode(...array)).replace(/[+/=]/g, (c) => ({ '+': '-', '/': '_', '=': '' }[c]));
}

async function generateCodeChallenge(verifier) {
  const encoder = new TextEncoder();
  const data = encoder.encode(verifier);
  const digest = await crypto.subtle.digest('SHA-256', data);
  return btoa(String.fromCharCode(...new Uint8Array(digest))).replace(/[+/=]/g, (c) => ({ '+': '-', '/': '_', '=': '' }[c]));
}

export default function Login() {
  const navigate = useNavigate();
  const [params] = useSearchParams();

  useEffect(() => {
    const code = params.get('code');
    if (!code) return;

    const verifier = sessionStorage.getItem('pkce_verifier');
    if (!verifier) return; // StrictMode double-fire guard — verifier already consumed
    sessionStorage.removeItem('pkce_verifier');

    client.post('/auth/google/callback', {
      code,
      code_verifier: verifier,
      redirect_uri: REDIRECT_URI,
    }).then(({ data }) => {
      setToken(data.access_token);
      // Check if B2B invite pending
      const pendingInvite = sessionStorage.getItem('pending_invite');
      if (pendingInvite) {
        sessionStorage.removeItem('pending_invite');
        navigate(`/invite/${pendingInvite}`);
      } else {
        navigate('/dashboard');
      }
    }).catch((err) => {
      console.error('Auth failed:', err?.response?.status, JSON.stringify(err?.response?.data));
      navigate('/login?error=auth_failed');
    });
  }, [params]);

  async function handleGoogleLogin() {
    const verifier = generateCodeVerifier();
    const challenge = await generateCodeChallenge(verifier);
    sessionStorage.setItem('pkce_verifier', verifier);

    const state = crypto.randomUUID();
    const url = new URL('https://accounts.google.com/o/oauth2/v2/auth');
    url.searchParams.set('client_id', GOOGLE_CLIENT_ID);
    url.searchParams.set('redirect_uri', REDIRECT_URI);
    url.searchParams.set('response_type', 'code');
    url.searchParams.set('scope', 'openid email profile');
    url.searchParams.set('code_challenge', challenge);
    url.searchParams.set('code_challenge_method', 'S256');
    url.searchParams.set('state', state);
    window.location.href = url.toString();
  }

  const error = params.get('error');

  return (
    <div style={styles.container}>
      <div style={styles.centered}>
        <div style={styles.card}>
          <h1 style={styles.title}>MindScope</h1>
          <p style={styles.subtitle}>AI-Powered Psychometric Assessment</p>
          {error && <p style={styles.error}>Authentication failed. Please try again.</p>}
          <button style={styles.button} onClick={handleGoogleLogin}>
            Sign in with Google
          </button>
          <p style={styles.disclaimer}>
            By continuing, you agree to our data processing terms in accordance with India's DPDP Act.
          </p>
        </div>
      </div>
      <Footer />
    </div>
  );
}

const styles = {
  container: { minHeight: '100vh', display: 'flex', flexDirection: 'column', background: '#f5f5f5' },
  centered: { flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '32px 16px' },
  card: { background: '#fff', padding: '48px', borderRadius: '12px', boxShadow: '0 4px 24px rgba(0,0,0,0.1)', textAlign: 'center', maxWidth: '400px', width: '100%' },
  title: { margin: 0, fontSize: '2rem', color: '#1a1a2e' },
  subtitle: { color: '#666', marginBottom: '32px' },
  button: { background: '#4285f4', color: '#fff', border: 'none', padding: '14px 32px', borderRadius: '8px', fontSize: '1rem', cursor: 'pointer', width: '100%' },
  error: { color: '#e53935', marginBottom: '16px' },
  disclaimer: { fontSize: '0.75rem', color: '#999', marginTop: '24px' },
};
