import { Link } from 'react-router-dom';

export default function Privacy() {
  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h1 style={styles.title}>Privacy Policy</h1>
        <p style={styles.meta}>Last updated: June 2026</p>

        <Section title="What we collect">
          <p>MindScope collects the following information when you use our platform:</p>
          <ul>
            <li>Name and email address (via Google OAuth sign-in)</li>
            <li>Assessment responses (RIASEC, Big Five, Aptitude items)</li>
            <li>Intake form data: life stage, field of study/work, career goals, challenges, satisfaction score</li>
            <li>Consent timestamp (required under India DPDP Act)</li>
            <li>Payment records (order ID, payment status — no card data stored)</li>
          </ul>
        </Section>

        <Section title="How we store it">
          <p>All data is stored on AWS infrastructure in the <strong>us-east-1</strong> region:</p>
          <ul>
            <li>Assessment data and user records: Amazon RDS PostgreSQL (encrypted at rest, AES-256 via AWS KMS)</li>
            <li>PDF reports: Amazon S3 (encrypted at rest, access via time-limited pre-signed URLs)</li>
            <li>Raw LLM outputs: stored in RDS for quality audit purposes</li>
            <li>Secrets (OAuth credentials, JWT keys): AWS Secrets Manager</li>
          </ul>
        </Section>

        <Section title="How we use it">
          <ul>
            <li>Assessment responses are used solely to generate your psychometric report</li>
            <li>Intake form values are passed to our AI model to personalise your report narrative</li>
            <li>Raw LLM outputs are retained for quality review and safety auditing</li>
            <li>Your data is <strong>never sold to third parties</strong></li>
          </ul>
        </Section>

        <Section title="India DPDP Act compliance">
          <p>
            We capture your explicit consent before processing assessment data. Your consent timestamp
            is recorded and stored. You have the right to request access to or deletion of your data
            at any time.
          </p>
        </Section>

        <Section title="Data deletion">
          <p>
            To request deletion of your account and all associated data, email us at{' '}
            <a href="mailto:anilhyd@gmail.com" style={styles.link}>anilhyd@gmail.com</a> with your
            registered email address. We will process your request within 30 days.
          </p>
        </Section>

        <Link to="/" style={styles.back}>← Back to Home</Link>
      </div>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div style={{ marginBottom: '28px' }}>
      <h2 style={{ fontSize: '1.1rem', color: '#1a1a2e', marginBottom: '10px' }}>{title}</h2>
      {children}
    </div>
  );
}

const styles = {
  container: { minHeight: '100vh', background: '#f5f5f5', padding: '40px 16px', display: 'flex', justifyContent: 'center' },
  card: { background: '#fff', borderRadius: '12px', padding: '40px', maxWidth: '720px', width: '100%', boxShadow: '0 4px 24px rgba(0,0,0,0.07)', lineHeight: 1.7, color: '#333', fontSize: '0.95rem' },
  title: { fontSize: '1.8rem', color: '#1a1a2e', marginBottom: '4px' },
  meta: { color: '#999', fontSize: '0.85rem', marginBottom: '32px' },
  link: { color: '#4285f4' },
  back: { display: 'inline-block', marginTop: '16px', color: '#4285f4', textDecoration: 'none', fontWeight: 500 },
};
