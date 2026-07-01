import { Link } from 'react-router-dom';

export default function Footer() {
  return (
    <footer role="contentinfo" style={styles.footer}>
      <span style={styles.copy}>© 2026 MindScope by DevPro Academy</span>
      <nav aria-label="Legal links" style={styles.links}>
        <Link to="/privacy" style={styles.link}>Privacy Policy</Link>
        <Link to="/terms" style={styles.link}>Terms</Link>
        <Link to="/refund" style={styles.link}>Refunds</Link>
        <Link to="/contact" style={styles.link}>Contact</Link>
      </nav>
    </footer>
  );
}

const styles = {
  footer: { borderTop: '1px solid #eee', padding: '20px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px', background: '#fff', marginTop: 'auto', fontSize: '0.82rem', color: '#888' },
  copy: {},
  links: { display: 'flex', gap: '20px' },
  link: { color: '#888', textDecoration: 'none' },
};
