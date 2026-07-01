export default function ErrorBanner({ message, onRetry }) {
  return (
    <div style={{ background: '#fff3f3', border: '1px solid #ffcdd2', color: '#c62828', padding: '12px 16px', borderRadius: '8px', marginBottom: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <span>{message}</span>
      {onRetry && <button onClick={onRetry} style={{ background: '#c62828', color: '#fff', border: 'none', padding: '6px 14px', borderRadius: '4px', cursor: 'pointer', fontSize: '0.85rem' }}>Retry</button>}
    </div>
  );
}
