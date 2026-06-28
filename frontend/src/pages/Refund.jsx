import { Link } from 'react-router-dom';

export default function Refund() {
  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h1 style={styles.title}>Refund &amp; Cancellation Policy</h1>
        <p style={styles.meta}>Last updated: June 2026</p>

        <Section title="Digital goods policy">
          <p>
            Assessment reports are digital goods delivered immediately after you complete your
            assessment. Because the report is generated and delivered upon completion, standard
            cancellation rights do not apply once the report has been delivered.
          </p>
        </Section>

        <Section title="When you are eligible for a full refund">
          <ul>
            <li>Your report fails to generate within <strong>24 hours</strong> of completing the assessment</li>
            <li>You experienced a technical error that prevented you from completing the assessment after payment</li>
          </ul>
          <p>In both cases, contact us within 48 hours with your session ID and we will issue a full refund.</p>
        </Section>

        <Section title="When refunds are not available">
          <ul>
            <li>After your PDF report has been generated and emailed to you</li>
            <li>If you changed your mind after completing the assessment</li>
            <li>If you did not complete the assessment within 30 days of payment</li>
          </ul>
        </Section>

        <Section title="How to request a refund">
          <p>
            Email <a href="mailto:anilhyd@gmail.com" style={styles.link}>anilhyd@gmail.com</a> with:
          </p>
          <ul>
            <li>Your registered email address</li>
            <li>Your session ID (visible in the dashboard)</li>
            <li>A brief description of the issue</li>
          </ul>
          <p>Refunds are processed within <strong>5–7 business days</strong> to the original payment method.</p>
        </Section>

        <Section title="B2B and institutional licenses">
          <p>
            Refund and cancellation terms for organisations purchasing bulk licenses are governed by
            the separate agreement signed with DevPro Academy / MindScope at the time of purchase.
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
