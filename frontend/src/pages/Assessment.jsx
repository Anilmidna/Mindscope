import { useEffect, useState, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import client from '../api/client';
import LoadingSpinner from '../components/LoadingSpinner';

const SECTIONS = ['RIASEC', 'OCEAN', 'Logical', 'Numerical', 'Verbal', 'Spatial'];
const TIMED = new Set(['Logical', 'Numerical', 'Verbal', 'Spatial']);
const LIKERT = ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'];

export default function Assessment() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [sectionIdx, setSectionIdx] = useState(null); // null = loading resume state
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState({});
  const [timeLeft, setTimeLeft] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [submitError, setSubmitError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [attentionFailed, setAttentionFailed] = useState(false);
  const startTimes = useRef({});
  const timerRef = useRef(null);

  // On mount: determine which section to resume from
  useEffect(() => {
    async function resolveStartSection() {
      try {
        const { data } = await client.get(`/sessions/${sessionId}`);
        // If session is already complete, jump straight to report
        if (data.status === 'complete' || data.status === 'report_ready') {
          navigate(`/report/${sessionId}`, { replace: true });
          return;
        }
        const completedSet = new Set(data.completed_domains || []);
        const resumeIdx = SECTIONS.findIndex((s) => !completedSet.has(s));
        setSectionIdx(resumeIdx === -1 ? 0 : resumeIdx);
      } catch {
        // Can't determine resume point — start from beginning
        setSectionIdx(0);
      }
    }
    resolveStartSection();
  }, [sessionId]);

  // Load questions whenever sectionIdx is set/changed
  useEffect(() => {
    if (sectionIdx === null) return;
    loadSection();
    return () => clearInterval(timerRef.current);
  }, [sectionIdx]);

  async function loadSection() {
    setLoading(true);
    setLoadError('');
    setAnswers({});
    try {
      const domain = SECTIONS[sectionIdx];
      const { data } = await client.get(`/sessions/${sessionId}/questions`, { params: { domain } });
      setQuestions(data.items);
      if (data.time_limit_seconds) {
        setTimeLeft(data.time_limit_seconds);
        timerRef.current = setInterval(() => {
          setTimeLeft((t) => {
            if (t <= 1) { clearInterval(timerRef.current); handleSubmit(true); return 0; }
            return t - 1;
          });
        }, 1000);
      } else {
        setTimeLeft(null);
        clearInterval(timerRef.current);
      }
    } catch (err) {
      if (err.response?.status === 402) {
        navigate(`/checkout/${sessionId}`, { replace: true });
        return;
      }
      setLoadError('Failed to load questions. Please check your connection and try again.');
    } finally {
      setLoading(false);
    }
  }

  function recordAnswer(itemId, value) {
    if (!startTimes.current[itemId]) startTimes.current[itemId] = Date.now();
    setAnswers((a) => ({ ...a, [itemId]: value }));
  }

  async function handleSubmit(forced = false) {
    clearInterval(timerRef.current);
    setSubmitting(true);
    setSubmitError('');

    const domain = SECTIONS[sectionIdx];

    // Check attention items
    const attItems = questions.filter((q) => q.item_id.startsWith('ATT') || q.item_id.startsWith('S-ATT') || q.item_id.startsWith('P-ATT'));
    let failed = false;
    for (const att of attItems) {
      const expected = att.expected_answer ?? att.expected_answer_range;
      const given = answers[att.item_id];
      if (Array.isArray(expected) && given !== undefined) {
        if (given < expected[0] || given > expected[1]) { failed = true; break; }
      } else if (expected !== undefined && given !== undefined && given !== expected) {
        failed = true; break;
      }
    }
    if (failed) setAttentionFailed(true);

    const items = questions.map((q) => ({
      item_id: q.item_id,
      answer: answers[q.item_id] ?? 0,
      response_time_ms: startTimes.current[q.item_id] ? Date.now() - startTimes.current[q.item_id] : null,
    }));

    try {
      await client.post(`/sessions/${sessionId}/responses`, { domain, items });
    } catch {
      setSubmitError('Failed to save responses. Please try again.');
      setSubmitting(false);
      return;
    }
    startTimes.current = {};

    if (sectionIdx < SECTIONS.length - 1) {
      setSectionIdx((i) => i + 1);
    } else {
      try {
        await client.post(`/sessions/${sessionId}/complete`);
        navigate(`/report/${sessionId}`);
      } catch {
        setSubmitError('Failed to complete assessment. Please try again.');
      }
    }
    setSubmitting(false);
  }

  const domain = sectionIdx !== null ? SECTIONS[sectionIdx] : '';
  const answered = Object.keys(answers).filter((k) => !k.startsWith('ATT')).length;
  const required = questions.filter((q) => !q.item_id.startsWith('ATT')).length;
  const canSubmit = answered >= required;
  const fmt = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;

  // Still resolving resume state
  if (sectionIdx === null) return <div style={styles.center}><LoadingSpinner message="Loading assessment..." /></div>;

  if (loading) return <div style={styles.center}><LoadingSpinner message="Loading questions..." /></div>;

  if (loadError) {
    return (
      <div style={styles.center}>
        <div style={styles.errorCard}>
          <h3>Could not load questions</h3>
          <p>{loadError}</p>
          <button style={styles.retryBtn} onClick={loadSection}>Try Again</button>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <span style={styles.logo}>MindScope</span>
        <div
          style={styles.progress}
          role="progressbar"
          aria-label={`Section ${sectionIdx + 1} of ${SECTIONS.length}`}
          aria-valuenow={sectionIdx + 1}
          aria-valuemin={1}
          aria-valuemax={SECTIONS.length}
        >
          {SECTIONS.map((s, i) => (
            <div key={s} style={{ ...styles.dot, background: i < sectionIdx ? '#4caf50' : i === sectionIdx ? '#4285f4' : '#ddd' }} title={s} />
          ))}
        </div>
        {timeLeft !== null && (
          <span style={{ ...styles.timer, color: timeLeft < 60 ? '#e53935' : '#333' }}>{fmt(timeLeft)}</span>
        )}
      </header>

      <main role="main" style={styles.main}>
        <h2 style={styles.sectionTitle}>{domain} {TIMED.has(domain) ? '(Timed)' : ''}</h2>
        <p aria-live="polite" style={styles.count}>{answered} / {required} answered</p>

        {attentionFailed && (
          <div style={styles.warning}>Some attention-check questions were not answered as expected. Please read carefully.</div>
        )}

        {submitError && (
          <div style={styles.errorBanner}>{submitError}</div>
        )}

        {questions.map((q) => (
          <div key={q.item_id} style={styles.card}>
            <p style={styles.qText}>{q.text}</p>
            {q.options ? (
              <div role="radiogroup" aria-label={q.text} style={styles.options}>
                {q.options.map((opt, i) => (
                  <label key={i} style={{ ...styles.optLabel, background: answers[q.item_id] === i ? '#e8f0fe' : '#f9f9f9' }}>
                    <input type="radio" name={q.item_id} value={i}
                      checked={answers[q.item_id] === i}
                      onChange={() => recordAnswer(q.item_id, i)} />
                    <span style={{ marginLeft: 8 }}>{opt}</span>
                  </label>
                ))}
              </div>
            ) : (
              <div role="radiogroup" aria-label={q.text} style={styles.likert}>
                {LIKERT.map((label, i) => (
                  <label key={i} style={styles.likertItem}>
                    <input type="radio" name={q.item_id} value={i + 1}
                      checked={answers[q.item_id] === i + 1}
                      onChange={() => recordAnswer(q.item_id, i + 1)} />
                    <span style={styles.likertLabel}>{label}</span>
                  </label>
                ))}
              </div>
            )}
          </div>
        ))}

        <button style={{ ...styles.btn, opacity: canSubmit ? 1 : 0.5 }}
          onClick={() => handleSubmit(false)} disabled={!canSubmit || submitting}>
          {submitting ? 'Saving...' : sectionIdx < SECTIONS.length - 1 ? `Next: ${SECTIONS[sectionIdx + 1]} →` : 'Complete Assessment →'}
        </button>
      </main>
    </div>
  );
}

const styles = {
  container: { minHeight: '100vh', background: '#f5f5f5' },
  center: { display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh' },
  errorCard: { background: '#fff', borderRadius: '12px', padding: '32px', textAlign: 'center', maxWidth: '400px', boxShadow: '0 4px 24px rgba(0,0,0,0.08)' },
  retryBtn: { background: '#4285f4', color: '#fff', border: 'none', padding: '10px 24px', borderRadius: '6px', cursor: 'pointer', marginTop: '12px', fontSize: '0.95rem' },
  header: { background: '#1a1a2e', color: '#fff', padding: '12px 24px', display: 'flex', alignItems: 'center', gap: '16px', position: 'sticky', top: 0, zIndex: 10 },
  logo: { fontWeight: 700, fontSize: '1.1rem', marginRight: 'auto' },
  progress: { display: 'flex', gap: '6px', alignItems: 'center' },
  dot: { width: 10, height: 10, borderRadius: '50%' },
  timer: { fontWeight: 700, fontSize: '1.1rem', minWidth: '50px', textAlign: 'right' },
  main: { maxWidth: '720px', margin: '0 auto', padding: '24px 16px' },
  sectionTitle: { fontSize: '1.4rem', color: '#1a1a2e', marginBottom: '4px' },
  count: { color: '#999', marginBottom: '20px', fontSize: '0.9rem' },
  warning: { background: '#fff3e0', border: '1px solid #ff9800', borderRadius: '6px', padding: '12px', marginBottom: '16px', color: '#e65100' },
  errorBanner: { background: '#fff3f3', border: '1px solid #ffcdd2', color: '#c62828', padding: '12px 16px', borderRadius: '8px', marginBottom: '16px' },
  card: { background: '#fff', borderRadius: '10px', padding: '20px', marginBottom: '16px', boxShadow: '0 2px 8px rgba(0,0,0,0.06)' },
  qText: { fontWeight: 500, marginBottom: '14px', lineHeight: 1.5, wordBreak: 'break-word' },
  likert: { display: 'flex', justifyContent: 'space-between', gap: '4px' },
  likertItem: { display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px', cursor: 'pointer', flex: '1 1 0', minWidth: 0 },
  likertLabel: { fontSize: '0.7rem', textAlign: 'center', color: '#555' },
  options: { display: 'flex', flexDirection: 'column', gap: '8px' },
  optLabel: { display: 'flex', alignItems: 'center', padding: '10px 14px', borderRadius: '6px', cursor: 'pointer', border: '1px solid #eee', wordBreak: 'break-word' },
  btn: { background: '#4285f4', color: '#fff', border: 'none', padding: '14px', borderRadius: '8px', fontSize: '1rem', cursor: 'pointer', width: '100%', marginTop: '8px' },
};
