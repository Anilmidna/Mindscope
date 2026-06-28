import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from "../api/client";

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
    <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
      <script src="https://checkout.razorpay.com/v1/checkout.js" />
      <div className="bg-white rounded-2xl shadow p-8 max-w-md w-full text-center">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Complete Your Assessment</h1>
        <p className="text-gray-500 mb-6">
          Get your full RIASEC + Big Five + Aptitude report with AI-generated career insights.
        </p>
        <div className="text-4xl font-bold text-indigo-600 mb-6">₹199</div>
        <ul className="text-left text-sm text-gray-600 space-y-2 mb-8">
          <li>✓ Full psychometric assessment (3 frameworks)</li>
          <li>✓ AI-generated personalized career report</li>
          <li>✓ PDF download + email delivery</li>
        </ul>
        {error && (
          <p className="text-red-500 text-sm mb-4">{error}</p>
        )}
        <button
          onClick={handlePay}
          disabled={loading}
          className="w-full bg-indigo-600 text-white py-3 rounded-lg font-semibold hover:bg-indigo-700 disabled:opacity-50"
        >
          {loading ? "Processing..." : "Pay ₹199 & Start Assessment"}
        </button>
      </div>
    </div>
  );
}
