import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from "../api/client";
import Footer from "../components/Footer";

export default function Checkout() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Check if already paid
    api.get(`/payments/status/${sessionId}`).then((res) => {
      if (res.data.status === "paid") {
        navigate(`/assessment/${sessionId}`);
      }
    });
  }, [sessionId, navigate]);

  async function handlePay() {
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.post("/payments/create-order", {
        session_id: sessionId,
      });

      const options = {
        key: data.key_id,
        amount: data.amount,
        currency: data.currency,
        name: "MindScope",
        description: "Psychometric Assessment Report",
        order_id: data.order_id,
        handler: async (response) => {
          try {
            await api.post("/payments/verify", {
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
            });
            navigate(`/assessment/${sessionId}`);
          } catch {
            setError("Payment verification failed. Contact support.");
          }
        },
        prefill: {},
        theme: { color: "#6366f1" },
      };

      const rzp = new window.Razorpay(options);
      rzp.on("payment.failed", () => {
        setError("Payment failed. Please try again.");
      });
      rzp.open();
    } catch (err) {
      setError(err.response?.data?.detail || "Could not initiate payment.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: '#f5f5f5' }}>
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '32px 16px' }}>
        <script src="https://checkout.razorpay.com/v1/checkout.js" />
        <div style={{ background: '#fff', borderRadius: '16px', boxShadow: '0 4px 24px rgba(0,0,0,0.1)', padding: '40px', maxWidth: '400px', width: '100%', textAlign: 'center' }}>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#111827', marginBottom: '8px' }}>Complete Your Assessment</h1>
          <p style={{ color: '#6b7280', marginBottom: '24px' }}>
            Get your full RIASEC + Big Five + Aptitude report with AI-generated career insights.
          </p>
          <div style={{ fontSize: '2.5rem', fontWeight: 700, color: '#4f46e5', marginBottom: '24px' }}>₹199</div>
          <ul style={{ textAlign: 'left', fontSize: '0.875rem', color: '#374151', marginBottom: '32px', listStyle: 'none', padding: 0, display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <li>✓ Full psychometric assessment (3 frameworks)</li>
            <li>✓ AI-generated personalized career report</li>
            <li>✓ PDF download + email delivery</li>
          </ul>
          {error && (
            <p style={{ color: '#ef4444', fontSize: '0.875rem', marginBottom: '16px' }}>{error}</p>
          )}
          <button
            onClick={handlePay}
            disabled={loading}
            style={{ width: '100%', background: '#4f46e5', color: '#fff', border: 'none', padding: '14px', borderRadius: '8px', fontSize: '1rem', fontWeight: 600, cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.5 : 1 }}
          >
            {loading ? "Processing..." : "Pay ₹199 & Start Assessment"}
          </button>
        </div>
      </div>
      <Footer />
    </div>
  );
}
