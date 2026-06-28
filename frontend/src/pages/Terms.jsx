import { Link } from 'react-router-dom';

export default function Terms() {
  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h1 style={styles.title}>Terms &amp; Conditions</h1>
        <p style={styles.meta}>Last updated: June 2026</p>

        <Section title="Nature of the service">
          <p>
            MindScope is a <strong>career-fit and strengths assessment tool</strong>. It is{' '}
            <strong>NOT a clinical, psychological, or diagnostic instrument</strong>. Reports are
            AI-generated based on your psychometric scores and intake form responses. They should be
            used as one input among many when making career decisions — not as a definitive evaluation
            of your abilities, personality, or mental health.
          </p>
        </Section>

        <Section title="Eligibility">
          <ul>
            <li>You must be 16 years of age or older to use MindScope independently</li>
            <li>Users under 16 require verifiable parental consent before assessment</li>
            <li>By using the platform you confirm you meet these requirements</li>
          </ul>
        </Section>

        <Section title="Assessment and reports">
          <ul>
            <li>One assessment per payment — each payment unlocks one full assessment session</li>
            <li>Reports are digital goods delivered immediately upon assessment completion</li>
            <li>You will receive your PDF report via email and can download it from the platform for 7 days</li>
            <li>Report content is AI-generated; MindScope does not guarantee specific career outcomes</li>
          </ul>
        </Section>

        <Section title="Payments and refunds">
          <p>
            Assessment reports are digital goods. See our{' '}
            <Link to="/refund" style={styles.link}>Refund & Cancellation Policy</Link> for full details.
            In summary: full refund if report fails to generate; no refund after report delivery.
          </p>
        </Section>

        <Section title="Limitation of liability">
          <p>
            DevPro Academy and MindScope are not liable for any career decisions, financial outcomes,
            or other consequences arising from use of or reliance on report content. The platform is
            provided as-is without warranties of any kind.
          </p>
        </Section>

        <Section title="Governing law">
          <p>
            These terms are governed by the laws of India. Any disputes shall be subject to the
            exclusive jurisdiction of courts in Hyderabad, Telangana.
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
