import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  getLiveGenerativeModel,
  ResponseModality,
  startAudioConversation,
} from "firebase/ai";
import { signInAnonymously } from "firebase/auth";
import {
  DEFAULT_STATE_CODE,
  getStateProfile,
  LANGUAGE_BY_CODE,
  LANGUAGE_OPTIONS,
} from "./data/indiaStateProfiles";
import {
  buildLanguageSwitchTurn,
  buildOpeningTurn,
  buildSystemInstruction,
  DEMO_PROMPTS,
} from "./lib/healthGuardrails";
import {
  GEMINI_LIVE_MODEL,
  getFirebaseServices,
  hasFirebaseConfig,
} from "./lib/firebase";
import { inferNearestState, requestCurrentPosition } from "./lib/location";
import type { CallState, LanguageCode } from "./types";
import "./styles.css";

const DEMO_EXAMPLES = [
  { icon: "🤒", bg: "rgba(255,107,107,0.15)", title: "Fever & Cold",    sub: "I have fever and body pain" },
  { icon: "❤️", bg: "rgba(255,79,97,0.15)",   title: "Chest Pain",      sub: "I have pain in my chest" },
  { icon: "🤰", bg: "rgba(192,132,252,0.15)", title: "Pregnancy Care",  sub: "I need pregnancy care guidance" },
  { icon: "👶", bg: "rgba(96,165,250,0.15)",  title: "Child Health",    sub: "My child is not eating well" },
  { icon: "🏥", bg: "rgba(52,211,153,0.15)",  title: "Find Hospitals",  sub: "Find nearby hospitals" },
];

const HEALTH_GUIDE = [
  { icon: "🤕", bg: "rgba(255,107,107,0.15)", title: "Fever & Cold",   tip: "Rest, drink fluids, take paracetamol if above 101°F. See a doctor if fever lasts 3+ days.", prompt: "I have fever and headache" },
  { icon: "❤️", bg: "rgba(255,79,97,0.15)",   title: "Chest Pain",     tip: "Chest pain with sweating or left arm pain is a medical emergency. Call 108 immediately.",    prompt: "I have chest pain" },
  { icon: "🤰", bg: "rgba(192,132,252,0.15)", title: "Pregnancy",      tip: "Regular antenatal check-ups are essential. Ask about iron supplements and vaccinations.",    prompt: "I need pregnancy care guidance" },
  { icon: "👶", bg: "rgba(96,165,250,0.15)",  title: "Child Health",   tip: "Ensure vaccinations are up to date. ORS is the first treatment for diarrhea in children.", prompt: "My child is not eating well" },
  { icon: "💉", bg: "rgba(52,211,153,0.15)",  title: "Vaccination",    tip: "India's National Immunization Schedule is free at all government health centers.",          prompt: "What vaccines does my baby need?" },
  { icon: "🏥", bg: "rgba(245,158,11,0.15)",  title: "Find Hospitals", tip: "JeevanRekha can find the nearest hospital using your GPS location.",                        prompt: "Find nearby hospitals" },
];

export default function App() {
  const [selectedStateCode, setSelectedStateCode] = useState(DEFAULT_STATE_CODE);
  const [selectedLanguageCode, setSelectedLanguageCode] = useState<LanguageCode>("hi-IN");
  const [callState, setCallState] = useState<CallState>("idle");
  const [callTimer, setCallTimer] = useState(0);
  const [isEmergency, setIsEmergency] = useState(false);
  const [coords, setCoords] = useState<{ lat: number; lng: number } | undefined>();
  const [aiStatus, setAiStatus] = useState<"Listening..." | "Thinking..." | "Speaking...">("Listening...");
  const [showLangModal, setShowLangModal] = useState(false);
  const [showExamples, setShowExamples] = useState(false);
  const [showHealthGuide, setShowHealthGuide] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [pendingLang, setPendingLang] = useState<LanguageCode>("hi-IN");

  const sessionRef    = useRef<any>(null);
  const controllerRef = useRef<any>(null);
  const timerRef      = useRef<number | null>(null);

  const selectedState    = getStateProfile(selectedStateCode);
  const selectedLanguage = LANGUAGE_BY_CODE[selectedLanguageCode];
  const orbClass = aiStatus === "Listening..." ? "listening" : aiStatus === "Thinking..." ? "thinking" : "speaking";

  useEffect(() => { handleUseLocation(); }, []);

  async function handleUseLocation() {
    try {
      const pos = await requestCurrentPosition();
      setCoords({ lat: pos.latitude, lng: pos.longitude });
      const nearest = inferNearestState(pos);
      if (nearest) {
        setSelectedStateCode(nearest.code);
        setSelectedLanguageCode(nearest.liveLanguage);
        setPendingLang(nearest.liveLanguage);
      }
    } catch (e) { console.error(e); }
  }

  async function startCall(promptText?: string) {
    if (!hasFirebaseConfig) {
      alert("Firebase configuration is missing. Please set VITE_FIREBASE_* env vars.");
      return;
    }
    setCallState("connecting");
    setAiStatus("Thinking...");
    setShowExamples(false);
    setShowHealthGuide(false);
    setShowLangModal(false);
    const services = getFirebaseServices();
    if (!services) { setCallState("idle"); return; }
    try {
      if (!services.auth.currentUser) await signInAnonymously(services.auth);
      const liveModel = getLiveGenerativeModel(services.ai, {
        model: GEMINI_LIVE_MODEL,
        systemInstruction: buildSystemInstruction(selectedState, selectedLanguageCode, coords),
        generationConfig: { responseModalities: [ResponseModality.AUDIO] },
      });
      const session    = await liveModel.connect();
      const controller = await startAudioConversation(session);
      sessionRef.current    = session;
      controllerRef.current = controller;
      setCallState("live");
      setAiStatus("Listening...");
      timerRef.current = window.setInterval(() => setCallTimer(p => p + 1), 1000);
      await session.send(promptText || buildOpeningTurn(selectedState, selectedLanguageCode), true);
    } catch (err) {
      console.error(err);
      setCallState("idle");
    }
  }

  async function endCall() {
    try {
      if (controllerRef.current) await controllerRef.current.stop();
      if (sessionRef.current)    await sessionRef.current.close();
    } catch (_) {}
    setCallState("idle");
    setCallTimer(0);
    setIsEmergency(false);
    if (timerRef.current) clearInterval(timerRef.current);
  }

  const fmt = (s: number) => {
    const m   = Math.floor(s / 60).toString().padStart(2, "0");
    const sec = (s % 60).toString().padStart(2, "0");
    return `${m}:${sec}`;
  };

  // ─── helpers to open modals exclusively ───────────────────────
  const openExamples     = () => { setShowLangModal(false); setShowHealthGuide(false); setShowExamples(true); };
  const openLang         = () => { setShowExamples(false);  setShowHealthGuide(false); setPendingLang(selectedLanguageCode); setShowLangModal(true); };
  const openHealthGuide  = () => { setShowExamples(false);  setShowLangModal(false);   setShowHealthGuide(true); };

  return (
    <div className="app-shell">

      {/* ── DESKTOP SIDEBAR ── */}
      <aside className="desktop-sidebar">
        <div className="sidebar-logo">
          <div className="logo-icon">❤️</div>
          <div>
            <div style={{ fontFamily: "var(--fd)", fontSize: 14, fontWeight: 700 }}>JeevanRekha</div>
            <div style={{ fontSize: 10, color: "var(--t3)", marginTop: 1 }}>AI Voice Health</div>
          </div>
        </div>
        {[
          { icon: "🏠", label: "Home",         action: () => {} },
          { icon: "📞", label: "Voice Call",   action: () => startCall() },
          { icon: "✨", label: "Examples",     action: openExamples },
          { icon: "🌐", label: "Language",     action: openLang },
          { icon: "📖", label: "Health Guide", action: openHealthGuide },
        ].map(item => (
          <div key={item.label} className="sidebar-nav-item" onClick={item.action}>
            <span>{item.icon}</span>
            <span>{item.label}</span>
          </div>
        ))}
      </aside>

      {/* ── MOBILE HEADER ── */}
      <header className="mob-header">
        <div className="mob-logo-block">
          <div className="mob-logo-title">Jeevanrekha</div>
          <div className="mob-logo-sub">AI Voice Health Assistant</div>
        </div>
        <div className="mob-menu-btn" onClick={openExamples}>☰</div>
      </header>

      {/* ── HOME SCREEN ── */}
      <div className="scroll-area">
        <div className="greeting-block">
          <h2>Namaste! I'm Jeevanrekha 👋</h2>
          <p>I am here to help you with<br />your health concerns.</p>
        </div>

        <div className="orb-wrap" onClick={() => startCall()}>
          <div className="orb-ring" />
          <div className="orb-body" />
        </div>

        <div className="start-call-wrap">
          <p style={{ marginBottom: 10, fontSize: 12, color: "var(--t3)" }}>Tap to start a voice call</p>
          <button className="btn-start" onClick={() => startCall()}>🎙️ Start Call</button>
        </div>

        <div className="info-cards-row">
          <div className="info-card" onClick={openLang}>
            <div className="info-card-label">🌐 Language</div>
            <div className="info-card-value">{selectedLanguage.nativeLabel}</div>
            <div className="info-card-sub">Change →</div>
          </div>
          <div className="info-card">
            <div className="info-card-label">📍 Location</div>
            <div className="info-card-value">{selectedState.name}</div>
            <div className="info-card-sub">Using GPS</div>
          </div>
        </div>

        <div className="examples-section">
          <h4>💡 You can say things like</h4>
          {DEMO_PROMPTS.slice(0, 3).map((p, i) => (
            <button key={i} className="example-chip" onClick={() => startCall(p)}>{p}</button>
          ))}
          <span className="view-all-link" onClick={openExamples}>View all examples →</span>
        </div>
      </div>

      {/* ── ACTIVE CALL SCREEN ── */}
      <AnimatePresence>
        {callState !== "idle" && (
          <motion.div
            key="call-screen"
            className="call-screen"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          >
            <div className="call-header">
              <div className="live-badge">
                <span className="live-dot" />
                Live · {fmt(callTimer)}
              </div>
              <button className="call-close-btn" onClick={endCall}>✕</button>
            </div>

            <div className="call-status-block">
              <h2>{aiStatus}</h2>
              <p>How can I help you today?</p>
            </div>

            <div className="call-orb-wrap">
              <div className="orb-ring" />
              <div className={`orb-body ${orbClass}`} />
            </div>

            <div className="waveform">
              {Array.from({ length: 18 }).map((_, i) => (
                <div
                  key={i}
                  className={`waveform-dot ${aiStatus === "Listening..." && i % 3 === 0 ? "active" : ""}`}
                  style={{ animationDelay: `${i * 0.07}s` }}
                />
              ))}
            </div>

            <div className="call-controls">
              <div className="ctrl-btn">
                <div className="ctrl-btn-circle">🔊</div>
                <span>Speaker</span>
              </div>
              <div className="ctrl-btn" onClick={endCall}>
                <div className="ctrl-btn-circle end-call">📞</div>
                <span style={{ color: "var(--danger)" }}>End Call</span>
              </div>
              <div className="ctrl-btn" onClick={() => setIsMuted(m => !m)}>
                <div className="ctrl-btn-circle">{isMuted ? "🔇" : "🎙️"}</div>
                <span>Mute</span>
              </div>
            </div>

            <div className="tips-card">
              <h4>✨ Tips</h4>
              <p>You can ask about symptoms, medications, doctors and more.</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── LANGUAGE MODAL ── */}
      <AnimatePresence>
        {showLangModal && (
          <motion.div
            key="lang-modal"
            className="lang-modal"
            initial={{ y: "100%" }} animate={{ y: 0 }} exit={{ y: "100%" }}
            transition={{ type: "spring", damping: 28, stiffness: 300 }}
          >
            <div className="lang-modal-header">
              <button className="back-btn" onClick={() => setShowLangModal(false)}>←</button>
              <h3>Select Language</h3>
            </div>
            <p className="lang-modal-sub">Choose your preferred language</p>
            <div className="lang-list">
              {LANGUAGE_OPTIONS.map(l => (
                <div
                  key={l.code}
                  className={`lang-option ${pendingLang === l.code ? "selected" : ""}`}
                  onClick={() => setPendingLang(l.code as LanguageCode)}
                >
                  <div className="lang-option-left">
                    <div>
                      <div className="lang-native">{l.nativeLabel}</div>
                      <div className="lang-eng">{l.label}</div>
                    </div>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    {l.availability === "prompt-guided" && <span className="preview-badge">Preview</span>}
                    <div className="lang-check">{pendingLang === l.code ? "✓" : ""}</div>
                  </div>
                </div>
              ))}
            </div>
            <div className="lang-modal-footer">
              <button
                className="btn-save-lang"
                onClick={() => {
                  setSelectedLanguageCode(pendingLang);
                  setShowLangModal(false);
                  if (callState === "live" && sessionRef.current) {
                    sessionRef.current.send(buildLanguageSwitchTurn(pendingLang), true);
                  }
                }}
              >
                🎙️ Save Language
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── EXAMPLES MODAL ── */}
      <AnimatePresence>
        {showExamples && (
          <motion.div
            key="examples-modal"
            className="examples-modal"
            initial={{ y: "100%" }} animate={{ y: 0 }} exit={{ y: "100%" }}
            transition={{ type: "spring", damping: 28, stiffness: 300 }}
          >
            <div className="examples-modal-header">
              <button className="back-btn" onClick={() => setShowExamples(false)}>←</button>
              <h3>Try an Example</h3>
            </div>
            <p className="examples-modal-sub">Tap on any example to start a demo conversation</p>
            <div className="ex-list">
              {DEMO_EXAMPLES.map((ex, i) => (
                <div key={i} className="ex-card" onClick={() => { setShowExamples(false); startCall(ex.sub); }}>
                  <div className="ex-icon" style={{ background: ex.bg }}>{ex.icon}</div>
                  <div>
                    <div className="ex-card-title">{ex.title}</div>
                    <div className="ex-card-sub">{ex.sub}</div>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── HEALTH GUIDE MODAL ── */}
      <AnimatePresence>
        {showHealthGuide && (
          <motion.div
            key="health-guide"
            className="examples-modal"
            initial={{ y: "100%" }} animate={{ y: 0 }} exit={{ y: "100%" }}
            transition={{ type: "spring", damping: 28, stiffness: 300 }}
          >
            <div className="examples-modal-header">
              <button className="back-btn" onClick={() => setShowHealthGuide(false)}>←</button>
              <h3>Health Guide</h3>
            </div>
            <p className="examples-modal-sub">Quick health tips — tap any to start a voice call</p>
            <div className="ex-list">
              {HEALTH_GUIDE.map((item, i) => (
                <div key={i} className="ex-card" onClick={() => { setShowHealthGuide(false); startCall(item.prompt); }}>
                  <div className="ex-icon" style={{ background: item.bg }}>{item.icon}</div>
                  <div>
                    <div className="ex-card-title">{item.title}</div>
                    <div className="ex-card-sub">{item.tip}</div>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── EMERGENCY OVERLAY ── */}
      <AnimatePresence>
        {isEmergency && (
          <motion.div
            key="emergency"
            className="emergency-overlay"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          >
            <div className="emergency-card">
              <div className="em-icon">⚠️</div>
              <div className="em-title">Emergency Detected</div>
              <p className="em-sub">Based on your symptoms, this may require immediate attention.</p>
              <button className="btn-em-call">📞 Call 108 Now</button>
              <button className="btn-em-hospital">🏥 Find Nearest Hospital</button>
              <div className="em-note">📍 Stay calm. Help is on the way.</div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

    </div>
  );
}
