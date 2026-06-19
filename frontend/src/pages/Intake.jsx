import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import client from '../api/client';

const LIFE_STAGES = [
  'School Student (Class 9-12)', 'Undergraduate Student', 'Final-Year / Graduate Student',
  'Working Professional (0-3 years)', 'Working Professional (3-10 years)',
  'Working Professional (10+ years)', 'Career Switcher', 'Currently Not Working',
];

const EDUCATION_LEVELS = [
  "Class 10 / SSC", "Class 12 / HSC", "Diploma", "Bachelor's Degree",
  "Master's Degree", "PhD / Doctorate", "Professional Certification",
];

const DOMAINS = [
  'Engineering / Technology', 'Science / Research', 'Commerce / Finance / Accounting',
  'Arts / Humanities / Social Sciences', 'Medicine / Healthcare', 'Law',
  'Design / Architecture', 'Management / Business', 'Education / Teaching',
  'Government / Public Service',
];

const WORK_STYLES = [
  'Structured corporate environment', 'Fast-paced startup', 'Research / academic setting',
  'Freelance / independent', 'Government / public sector', 'Not sure yet',
];

export default function Intake() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    life_stage: '', education_level: '', domain: '', specialization: '',
    future_goals: '', satisfaction: 5, challenges: '', preferred_work_style: '',
  });
  const [consentGiven, setConsentGiven] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  async function submit(e) {
    e.preventDefault();
    if (!form.life_stage || !form.future_goals) {
      setError('Please fill in all required fields.');
      return;
    }
    if (!consentGiven) {
      setError('Please accept the data processing consent to continue.');
      return;
    }
    setSaving(true);
    setError('');
    try {
      await client.post(`/sessions/${sessionId}/intake`, {
        ...form,
        consent_given_at: new Date().toISOString(),
      });
      navigate(`/assessment/${sessionId}`);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save. Please try again.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h2 style={styles.title}>Tell us about yourself</h2>
        <p style={styles.sub}>This helps us personalise your assessment and report.</p>
        {error && <p style={styles.error}>{error}</p>}
        <form onSubmit={submit}>
          <Field label="Where are you right now? *">
            <select value={form.life_stage} onChange={(e) => set('life_stage', e.target.value)} style={styles.input} required>
              <option value="">Select...</option>
              {LIFE_STAGES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </Field>

          <Field label="Highest education completed *">
            <select value={form.education_level} onChange={(e) => set('education_level', e.target.value)} style={styles.input} required>
              <option value="">Select...</option>
              {EDUCATION_LEVELS.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </Field>

          <Field label="Primary field of study or work">
            <select value={form.domain} onChange={(e) => set('domain', e.target.value)} style={styles.input}>
              <option value="">Select...</option>
              {DOMAINS.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </Field>

          <Field label="Specialization or job title">
            <input value={form.specialization} onChange={(e) => set('specialization', e.target.value)}
              placeholder="e.g. Computer Science, Data Analyst" style={styles.input} maxLength={100} />
          </Field>

          <Field label={`How satisfied are you with your current direction? ${form.satisfaction}/10`}>
            <input type="range" min={1} max={10} value={form.satisfaction}
              onChange={(e) => set('satisfaction', parseInt(e.target.value))} style={{ width: '100%' }} />
            <div style={styles.sliderLabels}><span>Very Unsatisfied</span><span>Very Satisfied</span></div>
          </Field>

          <Field label="What are you hoping to achieve in the next 2–3 years? *">
            <textarea value={form.future_goals} onChange={(e) => set('future_goals', e.target.value)}
              style={{ ...styles.input, height: '80px', resize: 'vertical' }}
              maxLength={200} placeholder="e.g. Switch to data science, get promoted, start a business" required />
            <small style={styles.charCount}>{form.future_goals.length}/200</small>
          </Field>

          <Field label="What's your biggest career challenge right now?">
            <textarea value={form.challenges} onChange={(e) => set('challenges', e.target.value)}
              style={{ ...styles.input, height: '60px', resize: 'vertical' }}
              maxLength={200} placeholder="e.g. Not sure which direction to go, feel stuck" />
          </Field>

          <Field label="Preferred work environment">
            <select value={form.preferred_work_style} onChange={(e) => set('preferred_work_style', e.target.value)} style={styles.input}>
              <option value="">Select...</option>
              {WORK_STYLES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </Field>

          <label style={styles.consentLabel}>
            <input
              type="checkbox"
              checked={consentGiven}
              onChange={(e) => setConsentGiven(e.target.checked)}
              style={{ marginRight: '10px', marginTop: '2px', flexShrink: 0 }}
            />
            <span>
              I consent to MindScope collecting and processing my assessment responses and personal information
              to generate my career report. My data will be stored securely and used only for this purpose,
              in accordance with the{' '}
              <a href="/privacy" target="_blank" rel="noopener noreferrer" style={{ color: '#4285f4' }}>
                Privacy Policy
              </a>.
            </span>
          </label>

          <button type="submit" style={{ ...styles.btn, opacity: consentGiven ? 1 : 0.5 }} disabled={saving || !consentGiven}>
            {saving ? 'Saving...' : 'Start Assessment →'}
          </button>
        </form>
      </div>
    </div>
  );
}

function Field({ label, children }) {
  return (
    <div style={{ marginBottom: '20px' }}>
      <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500, fontSize: '0.9rem' }}>{label}</label>
      {children}
    </div>
  );
}

const styles = {
  container: { minHeight: '100vh', background: '#f5f5f5', display: 'flex', justifyContent: 'center', padding: '32px 16px' },
  card: { background: '#fff', borderRadius: '12px', padding: '40px', maxWidth: '600px', width: '100%', boxShadow: '0 4px 24px rgba(0,0,0,0.08)' },
  title: { margin: '0 0 8px', fontSize: '1.6rem', color: '#1a1a2e' },
  sub: { color: '#666', marginBottom: '28px' },
  input: { width: '100%', padding: '10px 12px', borderRadius: '6px', border: '1px solid #ddd', fontSize: '0.95rem', boxSizing: 'border-box' },
  btn: { background: '#4285f4', color: '#fff', border: 'none', padding: '14px', borderRadius: '8px', fontSize: '1rem', cursor: 'pointer', width: '100%', marginTop: '8px' },
  error: { color: '#e53935', marginBottom: '16px', fontSize: '0.9rem' },
  sliderLabels: { display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#999', marginTop: '4px' },
  charCount: { color: '#999', fontSize: '0.75rem' },
  consentLabel: { display: 'flex', alignItems: 'flex-start', gap: '4px', fontSize: '0.82rem', color: '#555', lineHeight: 1.5, marginBottom: '20px', cursor: 'pointer' },
};
