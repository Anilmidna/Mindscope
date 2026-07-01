export default function LoadingSpinner({ message = 'Loading...' }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '64px 16px' }}>
      <div style={{ width: 40, height: 40, border: '3px solid #e0e0e0', borderTopColor: '#4285f4', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
      <p style={{ marginTop: 16, color: '#666', fontSize: '0.95rem' }}>{message}</p>
    </div>
  );
}
