import { Link } from 'react-router-dom';

export default function Contact() {
  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h1 style={styles.title}>Contact Us</h1>

        <p style={styles.intro}>
          MindScope is built and operated by <strong>DevPro Academy</strong>.
          We're here to help with support questions, refund requests, and data-related enquiries.
        </p>

        <div style={styles.contactBlock}>
          <div style={styles.contactRow}>
            <span style={styles.label}>Email</span>
            <a href="mailto:anilhyd@gmail.com" style={styles.link}>anilhyd@gmail.com</a>
          </div>
          <div style={styles.contactRow}>
            <span style={styles.label}>Response time</span>
            <span>Within 48 hours on business days</span>
          </div>
        </div>

        <div style={styles.topics}>
          <h2 style={styles.subtitle}>What to include in your email</h2>
          <ul>
            <li><strong>Support / technical issues:</strong> your registered email + a description of the problem</li>
            <li><strong>Refund requests:</strong> your registered email + session ID (visible in your dashboard)</li>
            <li><strong>Data deletion requests:</strong> your registered email + "Delete my data" in the subject line</li>
            <li><strong>B2B / institutional enquiries:</strong> your organisation name and what you're looking for</li>
          </ul>
        </div>

        <Link to="/" style={styles.back}>← Back to Home</Link>
      </div>
    </div>
  );
}

const styles = {
  container: { minHeight: '100vh', background: '#f5f5f5', padding: '40px 16px', display: 'flex', justifyContent: 'center' },
  card: { background: '#fff', borderRadius: '12px', padding: '40px', maxWidth: '600px', width: '100%', boxShadow: '0 4px 24px rgba(0,0,0,0.07)', lineHeight: 1.7, color: '#333', fontSize: '0.95rem' },
  title: { fontSize: '1.8rem', color: '#1a1a2e', marginBottom: '16px' },
  intro: { marginBottom: '28px', color: '#444' },
  contactBlock: { background: '#f8f9ff', borderRadius: '8px', padding: '20px 24px', marginBottom: '28px' },
  contactRow: { display: 'flex', gap: '16px', marginBottom: '8px', flexWrap: 'wrap' },
  label: { fontWeight: 600, minWidth: '120px', color: '#1a1a2e' },
  link: { color: '#4285f4' },
  subtitle: { fontSize: '1.05rem', color: '#1a1a2e', marginBottom: '10px' },
  topics: { marginBottom: '8px' },
  back: { display: 'inline-block', marginTop: '16px', color: '#4285f4', textDecoration: 'none', fontWeight: 500 },
};
