import React, { useState } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Upload, CheckCircle, FileText, Database, 
  Trash2, ArrowRight, RefreshCcw, Sparkles, ChevronRight,
  User, DollarSign, Activity
} from 'lucide-react';

const API_BASE = "http://localhost:8000";

const App = () => {
  const [file, setFile] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [reviewData, setReviewData] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);

  const resetAll = () => {
    setFile(null);
    setReviewData(null);
    setIsProcessing(false);
    setSuccess(false);
  };

  const handleFileChange = (e) => {
    if (e.target.files[0]) setFile(e.target.files[0]);
  };

  const startTranscription = async () => {
    if (!file) return;
    setIsProcessing(true);
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await axios.post(`${API_BASE}/process-audio`, formData);
      setReviewData(res.data);
    } catch (err) {
      alert("AI Brain Error: " + err.message);
    } finally {
      setIsProcessing(false);
    }
  };

  const confirmAndPush = async () => {
    setIsSubmitting(true);
    try {
      await axios.post(`${API_BASE}/submit-to-zoho`, { 
        transcript: reviewData.transcript,
        filename: reviewData.filename 
      });
      setSuccess(true);
      setReviewData(null);
    } catch (err) {
      alert("Zoho Push Failed: " + err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const StepIndicator = ({ step, label, active, done }) => (
    <div className={`stepper-item ${active ? 'active' : ''}`} style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
      <div className="step-circle" style={{ 
        background: done ? 'var(--success)' : (active ? 'var(--primary)' : '#f1f5f9'),
        color: done || active ? 'white' : 'var(--text-muted)'
      }}>
        {done ? <CheckCircle size={20} /> : step}
      </div>
      <span style={{ fontSize: '0.9rem', fontWeight: 600, color: active ? 'var(--text-main)' : 'var(--text-muted)' }}>{label}</span>
    </div>
  );

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: 'var(--bg-main)' }}>
      {/* FIXED HEADER SECTION */}
      <header style={{ 
        padding: '1rem 4rem', background: 'rgba(255,255,255,0.8)', backdropFilter: 'blur(10px)', 
        borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', 
        alignItems: 'center', zIndex: 100
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          <div style={{ background: 'var(--primary)', padding: '8px', borderRadius: '10px', boxShadow: '0 4px 15px var(--primary-glow)' }}>
            <Sparkles color="white" size={24} />
          </div>
          <div>
            <h1 style={{ fontSize: '1.5rem', fontWeight: 800, letterSpacing: '-1px', color: 'var(--text-main)' }}>
              LEAD <span style={{ fontWeight: 300, color: 'var(--text-muted)' }}>NEXUS</span>
            </h1>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', letterSpacing: '0.5px' }}>PREMIUM LEAD PROCESSING COMMAND</p>
          </div>
        </div>

        <nav className="stepper-nav" style={{ display: 'flex', gap: '2rem', padding: '8px 24px', borderRadius: '50px', border: '1px solid var(--border)' }}>
          <StepIndicator step={1} label="UPLOAD" active={!reviewData && !success} done={!!reviewData || success} />
          <ChevronRight size={14} color="var(--border)" />
          <StepIndicator step={2} label="REFINE" active={!!reviewData} done={success} />
          <ChevronRight size={14} color="var(--border)" />
          <StepIndicator step={3} label="SYNC" active={success} done={success} />
        </nav>
      </header>

      {/* SCROLLABLE MAIN CONTENT */}
      <main style={{ flex: 1, overflowY: 'auto', padding: '0 10%', paddingBottom: '12rem' }}>
        <AnimatePresence mode="wait">
          
          {!reviewData && !success && (
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} key="upload-step" style={{ height: '100%', display: 'flex', alignItems: 'center' }}>
              <div className="glass-card" style={{ width: '100%', padding: '6rem 2rem', textAlign: 'center' }}>
                <div style={{ maxWidth: '450px', margin: '0 auto' }}>
                  {!file ? (
                    <label style={{ cursor: 'pointer' }}>
                      <div style={{ background: '#f8fafc', padding: '3rem', borderRadius: '40px', border: '2px dashed var(--border)', marginBottom: '1.5rem' }}>
                        <Upload size={48} color="var(--primary)" />
                      </div>
                      <h3 style={{ color: 'var(--text-main)', marginBottom: '1rem' }}>SECURE LEAD UPLOAD</h3>
                      <div style={{ display: 'flex', gap: '8px', justifyContent: 'center', marginBottom: '2rem', flexWrap: 'wrap' }}>
                        {['MP3', 'WAV', 'M4A', 'OGG', 'FLAC', 'WEBM', 'MP4'].map(ext => (
                          <span key={ext} style={{ fontSize: '0.65rem', fontWeight: 800, padding: '4px 10px', background: '#f1f5f9', color: 'var(--text-muted)', borderRadius: '6px', border: '1px solid var(--border)' }}>{ext}</span>
                        ))}
                      </div>
                      <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>Select CRM audio for High-Fidelity AI Transcription</p>
                      <input type="file" onChange={handleFileChange} style={{ display: 'none' }} />
                    </label>
                  ) : (
                    <div style={{ background: '#f8fafc', padding: '2.5rem', borderRadius: '40px', border: '1.5px solid var(--primary)' }}>
                      <FileText size={40} color="var(--primary)" style={{ marginBottom: '1rem' }} />
                      <h4 style={{ wordBreak: 'break-all', marginBottom: '1.5rem', color: 'var(--text-main)' }}>{file.name}</h4>
                      <div style={{ display: 'flex', gap: '15px', justifyContent: 'center' }}>
                         <button className="btn-premium" onClick={startTranscription} disabled={isProcessing}>
                          {isProcessing ? 'TRANScribing...' : 'INITIALIZE'}
                        </button>
                        <button className="btn-outline" onClick={() => setFile(null)}><Trash2 size={20} /></button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          )}

          {reviewData && !success && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} key="refine-step">
              <div className="glass-card" style={{ padding: '1.2rem 2.5rem 2.5rem 2.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '1rem' }}>
                  <FileText color="var(--primary)" size={20} />
                  <h2 style={{ fontSize: '1.2rem', color: 'var(--text-main)' }}>Expert Dialogue Transcription</h2>
                </div>
                <textarea 
                  value={reviewData.transcript} 
                  onChange={(e) => setReviewData({...reviewData, transcript: e.target.value})}
                  style={{ 
                    width: '100%', height: 'calc(100vh - 280px)', background: '#f8fafc', border: '1px solid var(--border)', 
                    borderRadius: '16px', padding: '1.5rem', color: 'var(--text-main)', fontSize: '1.05rem', lineHeight: '1.8',
                    outline: 'none', resize: 'none'
                  }}
                />
              </div>
            </motion.div>
          )}

          {success && (
            <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} key="success-step" style={{ height: '100%', display: 'flex', alignItems: 'center' }}>
              <div className="glass-card" style={{ width: '100%', padding: '6rem 2rem', textAlign: 'center' }}>
                <div style={{ background: 'var(--primary)', width: '80px', height: '80px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 2rem' }}>
                  <CheckCircle size={40} color="white" />
                </div>
                <h1 style={{ fontSize: '2rem', fontWeight: 800, marginBottom: '1rem', color: 'var(--text-main)' }}>VALIDATED</h1>
                <p style={{ color: 'var(--text-muted)', marginBottom: '2rem' }}>Data pushed to Zoho India and Drive Archive.</p>
                <button className="btn-premium" onClick={resetAll} style={{ margin: '0 auto' }}>NEW CALL</button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* FIXED BOTTOM ACTION DOCK */}
      {reviewData && !success && (
        <div style={{ 
          position: 'fixed', bottom: 0, left: 0, width: '100%', background: 'rgba(255,255,255,0.95)', 
          backdropFilter: 'blur(10px)', borderTop: '1px solid var(--border)', padding: '0.8rem 4rem', 
          display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.8rem', zIndex: 100 
        }}>
          {/* AI ADVISORY ALERT */}
          <div style={{ 
            display: 'flex', alignItems: 'center', gap: '8px', background: '#fffbeb', 
            border: '1px solid #fde68a', padding: '6px 15px', borderRadius: '30px',
            color: '#b45309', fontSize: '0.75rem', fontWeight: 600
          }}>
             <Sparkles size={12} /> AI ADVISORY: VERIFY FOR 100% LITERAL TRUTH BEFORE FINAL SYNC.
          </div>

          <div style={{ display: 'flex', gap: '15px' }}>
            <button className="btn-premium" onClick={confirmAndPush} disabled={isSubmitting} style={{ width: '300px', padding: '12px', borderRadius: '12px', fontSize: '1rem' }}>
              <Database size={18} />
              {isSubmitting ? 'SYNCING...' : 'FINAL SYNC TO ZOHO'}
            </button>
            <button className="btn-outline" onClick={resetAll} style={{ width: '120px', borderRadius: '12px', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px', padding: '12px' }}>
              <Trash2 size={16} /> CANCEL
            </button>
          </div>
          <footer style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
            &copy; 2026 ZOHO LEAD ARCHITECT // HIGH-INTELLIGENCE CRM PIPELINE
          </footer>
        </div>
      )}

      {!reviewData && !success && (
         <div style={{ position: 'fixed', bottom: 0, left: 0, width: '100%', padding: '2rem', textAlign: 'center', opacity: 0.5 }}>
            <p style={{ fontSize: '0.75rem' }}>&copy; 2026 ZOHO LEAD ARCHITECT</p>
         </div>
      )}
    </div>
  );
};

export default App;
