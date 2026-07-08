import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import {
  ArrowLeft,
  ArrowUp,
  Bot,
  Braces,
  BrainCircuit,
  CheckCircle2,
  ChevronDown,
  Clapperboard,
  Database,
  Film,
  History,
  LoaderCircle,
  LogIn,
  LogOut,
  Mail,
  MessageCircleMore,
  Plus,
  RefreshCw,
  Search,
  Sparkles,
  Star,
  Trash2,
  UserRound,
  WifiOff,
  Workflow,
  X,
} from "lucide-react";

import MovieConversation from "./components/MovieConversation";
import {
  createId,
  deleteRemoteThread,
  loadLocalThreads,
  loadRemoteMovieThreads,
  mergeThreads,
  saveLocalThreads,
  syncThreadToSupabase,
} from "./lib/chatStore";
import { isSupabaseConfigured, supabase } from "./lib/supabase";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const POSTER_BASE_URL = "https://image.tmdb.org/t/p/w500";
const WORKSPACE_STORAGE_KEY = "cinematch:workspace:v1";
const ENTRY_STORAGE_KEY = "cinematch:entry:v1";
const DEMO_USER_STORAGE_KEY = "cinematch:demo-user:v1";

const SUGGESTIONS = [
  "Film seperti Interstellar",
  "Rekomendasi mirip The Dark Knight",
  "Saya ingin nonton film seperti Toy Story",
];

const LLM_SUGGESTIONS = [
  "Film action dengan aktor Christian Bale dan rating minimal 7",
  "Film Korea setelah 2015 berdurasi maksimal 130 menit",
  "Film karya Christopher Nolan bertema perjalanan waktu",
];

const INITIAL_MESSAGES = [
  {
    id: "welcome",
    role: "assistant",
    content:
      "Cari satu film acuan dulu. Setelah kamu pilih salah satu movie, chat akan terkunci ke movie itu dan semua pertanyaan lanjutannya masuk ke thread film tersebut.",
  },
];

const INTENT_LABELS = {
  reference_title: "Film acuan",
  preferred_genres: "Genre",
  actors: "Aktor",
  directors: "Sutradara",
  keywords: "Keyword",
  original_languages: "Bahasa",
  min_rating: "Rating minimum",
  max_rating: "Rating maksimum",
  release_year_from: "Tahun mulai",
  release_year_to: "Tahun akhir",
  min_runtime: "Durasi minimum",
  max_runtime: "Durasi maksimum",
};

function loadWorkspace() {
  try {
    return JSON.parse(localStorage.getItem(WORKSPACE_STORAGE_KEY) || "{}") || {};
  } catch {
    return {};
  }
}

function loadDemoUser() {
  try {
    return JSON.parse(localStorage.getItem(DEMO_USER_STORAGE_KEY) || "null");
  } catch {
    return null;
  }
}

function detectedIntentEntries(intent = {}) {
  return Object.entries(INTENT_LABELS)
    .map(([key, label]) => ({ key, label, value: intent[key] }))
    .filter(({ value }) => {
      if (Array.isArray(value)) return value.length > 0;
      return value !== null && value !== undefined && value !== "";
    });
}

function displayIntentValue(value) {
  if (Array.isArray(value)) return value.join(", ");
  return String(value);
}

function posterUrl(path) {
  return path ? `${POSTER_BASE_URL}${path}` : null;
}

function formatScore(value) {
  return typeof value === "number" ? `${Math.round(value * 100)}%` : "-";
}

function formatThreadTime(value) {
  return new Intl.DateTimeFormat("id-ID", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function userLabel(session, demoUser) {
  return session?.user?.email || demoUser?.email || "Local demo user";
}

function QueryAnalysisDrawer({ analysis }) {
  const [open, setOpen] = useState(false);
  if (!analysis) return null;

  const intentEntries = detectedIntentEntries(analysis.extracted_intent);
  const parameters = analysis.execution_parameters || {};
  const modeLabel = {
    similarity: "Similarity search",
    discovery: "Metadata discovery",
    clarification: "Clarification",
  }[analysis.execution_mode];

  const drawer = open
    ? createPortal(
        <div className="drawer-layer" role="presentation">
          <button
            className="drawer-scrim"
            type="button"
            onClick={() => setOpen(false)}
            aria-label="Tutup query trace"
          />
          <aside className="query-trace-drawer" aria-label="Analisis dan eksekusi query">
            <header className="trace-drawer-header">
              <div>
                <span className="trace-overline"><Workflow size={13} /> Query trace</span>
                <h3>Bagaimana sistem membaca query</h3>
              </div>
              <button type="button" onClick={() => setOpen(false)} aria-label="Tutup query trace">
                <X size={18} />
              </button>
            </header>

            <div className="trace-badges drawer-badges">
              <span>{analysis.interpreter === "openai" ? "OpenAI intent parser" : "Fallback parser"}</span>
              <strong>{modeLabel}</strong>
            </div>

            <article className="trace-stage intent-stage">
              <div className="stage-number">01</div>
              <div className="stage-copy">
                <div className="stage-title"><BrainCircuit size={16} /> Yang diambil dari query user</div>
                <p className="stage-note">
                  {analysis.interpreter === "openai"
                    ? `Diekstrak oleh ${analysis.llm_model || "OpenAI"} sebagai structured intent.`
                    : "Diambil oleh parser pola karena LLM tidak digunakan."}
                </p>
                <div className="intent-values">
                  {intentEntries.length > 0 ? intentEntries.map(({ key, label, value }) => (
                    <div className="intent-row" key={key}>
                      <span>{label}</span>
                      <strong>{displayIntentValue(value)}</strong>
                    </div>
                  )) : <p className="empty-intent">Belum ada parameter pencarian yang terdeteksi.</p>}
                </div>
              </div>
            </article>

            <article className="trace-stage execution-stage">
              <div className="stage-number">02</div>
              <div className="stage-copy">
                <div className="stage-title"><Database size={16} /> Yang dijalankan backend</div>
                <p className="stage-note">LLM hanya membantu membaca intent; backend tetap menjalankan pipeline pencarian.</p>
                <code className="backend-query">{analysis.backend_query}</code>
                <div className="execution-facts">
                  {parameters.qdrant_collection && <span>Collection <strong>{parameters.qdrant_collection}</strong></span>}
                  {parameters.candidate_pool_target && <span>Candidate pool <strong>{parameters.candidate_pool_target}</strong></span>}
                  {parameters.top_k && <span>Final top-k <strong>{parameters.top_k}</strong></span>}
                </div>
              </div>
            </article>

            <ol className="execution-steps drawer-steps">
              {analysis.steps.map((step, index) => (
                <li key={`${index}-${step}`}><span>{index + 1}</span><p>{step}</p></li>
              ))}
            </ol>

            <details className="raw-intent">
              <summary><Braces size={14} /> Lihat raw structured intent <ChevronDown size={14} /></summary>
              <pre>{JSON.stringify(analysis.extracted_intent, null, 2)}</pre>
            </details>
          </aside>
        </div>,
        document.body,
      )
    : null;

  return (
    <>
      <button className="trace-drawer-trigger" type="button" onClick={() => setOpen(true)}>
        <Workflow size={15} />
        <span>Open query trace</span>
        <strong>{modeLabel}</strong>
      </button>

      {drawer}
    </>
  );
}

function MoviePoster({ movie, priority = false }) {
  const [failed, setFailed] = useState(false);
  const url = posterUrl(movie.poster_path);

  if (!url || failed) {
    return (
      <div className="poster-fallback" aria-label={`Poster ${movie.title} tidak tersedia`}>
        <Film size={30} strokeWidth={1.5} />
        <span>{movie.title}</span>
      </div>
    );
  }

  return (
    <img
      className="movie-poster"
      src={url}
      alt={`Poster ${movie.title}`}
      loading={priority ? "eager" : "lazy"}
      onError={() => setFailed(true)}
    />
  );
}

function RecommendationCard({ movie, index, onDiscuss }) {
  const displayedScore = movie.score_type === "discovery"
    ? movie.hybrid_score
    : movie.similarity_score;
  const scoreLabel = movie.score_type === "discovery"
    ? "Discovery score"
    : "Content match";
  const facts = [movie.release_year, movie.runtime && `${movie.runtime} min`, movie.original_language?.toUpperCase()]
    .filter(Boolean)
    .join(" · ");

  return (
    <article className="movie-card" style={{ "--delay": `${index * 55}ms` }}>
      <button className="movie-card-hitbox" type="button" onClick={() => onDiscuss(movie)}>
        <span className="sr-only">Lock chat ke {movie.title}</span>
      </button>
      <div className="poster-wrap">
        <MoviePoster movie={movie} priority={index < 2} />
        <span className="rank">{String(index + 1).padStart(2, "0")}</span>
        <div className="poster-hover-info" aria-hidden="true">
          <div className="hover-topline">
            <span>{movie.release_year || "Tahun -"}</span>
            <span>{movie.runtime ? `${movie.runtime} min` : "Durasi -"}</span>
            <span>{movie.original_language?.toUpperCase() || "Lang -"}</span>
          </div>
          <strong>{movie.title}</strong>
          <p>{movie.genres || "Genre tidak tersedia"}</p>
          {movie.director && <p>Sutradara: {movie.director}</p>}
          {movie.reason && <em>{movie.reason}</em>}
          <small><MessageCircleMore size={13} /> Klik poster untuk lock chat</small>
        </div>
      </div>
      <div className="movie-copy compact-card-copy">
        <div className="movie-heading">
          <div>
            <h3>{movie.title}</h3>
            <p>{facts || "Metadata tidak tersedia"}</p>
          </div>
          <div className="rating" title="TMDB vote average">
            <Star size={14} fill="currentColor" />
            {movie.vote_average?.toFixed(1) || "-"}
          </div>
        </div>

        <div className="score-row">
          <span>{scoreLabel}</span>
          <strong>{formatScore(displayedScore)}</strong>
        </div>
        <div className="score-track" aria-hidden="true">
          <span style={{ width: `${Math.min((displayedScore || 0) * 100, 100)}%` }} />
        </div>
      </div>
    </article>
  );
}

function MovieDetailPanel({ movie, onBack, onDiscuss }) {
  const displayedScore = movie.score_type === "discovery"
    ? movie.hybrid_score
    : movie.similarity_score;

  return (
    <article className="movie-detail-panel">
      <button className="detail-back" type="button" onClick={onBack}>
        <ArrowLeft size={16} /> Back to movie list
      </button>

      <div className="detail-hero">
        {movie.backdrop_path && (
          <img
            className="detail-backdrop"
            src={`https://image.tmdb.org/t/p/w1280${movie.backdrop_path}`}
            alt=""
            aria-hidden="true"
          />
        )}
        <div className="detail-poster">
          <MoviePoster movie={movie} priority />
        </div>
        <div className="detail-copy">
          <span className="context-kicker"><Film size={13} /> Movie detail</span>
          <h3>{movie.title}</h3>
          <p className="detail-meta">
            {[movie.release_year, movie.genres, movie.runtime && `${movie.runtime} min`, movie.original_language?.toUpperCase()]
              .filter(Boolean)
              .join(" · ")}
          </p>
          <div className="detail-facts">
            <span><Star size={14} fill="currentColor" /> {movie.vote_average?.toFixed(1) || "-"}</span>
            <span>Match <strong>{formatScore(displayedScore)}</strong></span>
            {movie.director && <span>Director <strong>{movie.director}</strong></span>}
          </div>
          {movie.reason && <p className="detail-reason">{movie.reason}</p>}
          <button className="detail-lock-button" type="button" onClick={() => onDiscuss(movie)}>
            <MessageCircleMore size={16} /> Lock chat ke film ini
          </button>
        </div>
      </div>

      <div className="detail-sections">
        <section>
          <span>Overview</span>
          <p>{movie.overview || "Sinopsis belum tersedia di metadata."}</p>
        </section>
        <section>
          <span>Cast</span>
          <p>{movie.cast || "Data cast belum tersedia."}</p>
        </section>
        <section>
          <span>Keywords</span>
          <p>{movie.keywords || "Keyword belum tersedia."}</p>
        </section>
      </div>
    </article>
  );
}

function LockedMovieSummary({ thread }) {
  const movie = thread.movie;

  return (
    <article className="locked-movie-panel">
      <div className="locked-poster-frame">
        <MoviePoster movie={movie} priority />
      </div>
      <div className="locked-movie-copy">
        <span className="context-kicker"><MessageCircleMore size={13} /> Movie sedang dibahas</span>
        <h3>{movie.title}</h3>
        <p className="locked-meta">
          {[movie.release_year, movie.genres, movie.runtime && `${movie.runtime} min`].filter(Boolean).join(" · ")}
        </p>
        <div className="locked-facts">
          <span><Star size={14} fill="currentColor" /> {movie.vote_average?.toFixed(1) || "-"}</span>
          {movie.director && <span>Sutradara: <strong>{movie.director}</strong></span>}
          <span>{thread.messages.length} pesan di thread ini</span>
        </div>
        {movie.cast && <p className="cast-line">Cast: {movie.cast}</p>}
        {movie.overview && <p className="locked-overview">{movie.overview}</p>}
        <p className="locked-note">
          Panel kanan ini sekarang menampilkan movie yang sedang terkunci. Kalau mau mencari rekomendasi lain,
          tekan “Chat baru / cari movie lain” di sidebar.
        </p>
      </div>
    </article>
  );
}

function SkeletonGrid() {
  return (
    <div className="recommendation-grid" aria-label="Memuat rekomendasi">
      {[0, 1, 2, 3].map((item) => (
        <div className="movie-card skeleton-card" key={item}>
          <div className="skeleton poster-skeleton" />
          <div className="movie-copy">
            <div className="skeleton title-skeleton" />
            <div className="skeleton text-skeleton" />
            <div className="skeleton text-skeleton short" />
          </div>
        </div>
      ))}
    </div>
  );
}

function LandingPage({ onLogin, onRegister }) {
  return (
    <main className="landing-page">
      <nav className="landing-nav">
        <a className="brand" href="#top" aria-label="CineMatch home">
          <span className="brand-mark"><Clapperboard size={22} /></span>
          <span>CineMatch</span>
        </a>
        <div className="landing-actions">
          <button type="button" onClick={onLogin}>Login</button>
          <button type="button" className="primary" onClick={onRegister}>Register</button>
        </div>
      </nav>

      <section className="hero">
        <div className="hero-copy">
          <span className="eyebrow"><Sparkles size={15} /> Word2Vec + LLM intent + nested chat</span>
          <h1>Find the next film, then talk inside its story.</h1>
          <p>
            Mulai dari film yang kamu suka, lihat rekomendasi, lalu klik satu movie untuk membuka chat khusus.
            History tiap movie tetap rapi seperti sidebar ChatGPT.
          </p>
          <div className="hero-cta">
            <button type="button" onClick={onRegister}>Mulai sekarang</button>
            <button type="button" className="ghost" onClick={onLogin}>Saya sudah punya akun</button>
          </div>
        </div>

        <div className="hero-card" aria-hidden="true">
          <div className="hero-ticket">
            <span>QUERY</span>
            <strong>“carikan saya film yang mirip dengan Interstellar”</strong>
          </div>
          <div className="hero-thread-card">
            <MessageCircleMore size={18} />
            <div>
              <strong>Interstellar thread</strong>
              <small>Context locked · 7 messages</small>
            </div>
          </div>
          <div className="hero-thread-card offset">
            <MessageCircleMore size={18} />
            <div>
              <strong>The Martian thread</strong>
              <small>Ask director, cast, genre, rating...</small>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}

function AuthPage({ mode, onModeChange, onBack, onAuthenticated }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);
  const isRegister = mode === "register";

  async function submit(event) {
    event.preventDefault();
    if (!email.trim()) return;

    setLoading(true);
    setStatus("");

    if (!isSupabaseConfigured) {
      const demoUser = { id: "local-demo", email: email.trim(), mode: "local" };
      localStorage.setItem(DEMO_USER_STORAGE_KEY, JSON.stringify(demoUser));
      localStorage.setItem(ENTRY_STORAGE_KEY, "app");
      onAuthenticated({ demoUser });
      setLoading(false);
      return;
    }

    const payload = { email: email.trim(), password };
    const { data, error } = isRegister
      ? await supabase.auth.signUp(payload)
      : await supabase.auth.signInWithPassword(payload);

    if (error) {
      setStatus(error.message);
      setLoading(false);
      return;
    }

    if (data.session) {
      localStorage.setItem(ENTRY_STORAGE_KEY, "app");
      onAuthenticated({ session: data.session });
    } else {
      setStatus("Akun dibuat. Jika Supabase meminta email confirmation, cek inbox lalu login lagi.");
    }
    setLoading(false);
  }

  return (
    <main className="auth-page">
      <button type="button" className="back-link" onClick={onBack}>
        <ArrowLeft size={16} /> Kembali ke landing
      </button>

      <section className="auth-card-page">
        <span className="auth-kicker">{isRegister ? "Create account" : "Welcome back"}</span>
        <h1>{isRegister ? "Register CineMatch" : "Login CineMatch"}</h1>
        <p>
          {isSupabaseConfigured
            ? "Login menyimpan nested movie chat ke Supabase agar history tidak hilang."
            : "Supabase belum dikonfigurasi, jadi form ini memakai akun demo lokal di browser."}
        </p>

        <form onSubmit={submit}>
          <label htmlFor="auth-email">Email</label>
          <div className="auth-input-row">
            <Mail size={16} />
            <input
              id="auth-email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.com"
              required
            />
          </div>

          <label htmlFor="auth-password">Password</label>
          <div className="auth-input-row">
            <LogIn size={16} />
            <input
              id="auth-password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder={isSupabaseConfigured ? "Minimal 6 karakter" : "Boleh diisi apa saja untuk demo"}
              minLength={isSupabaseConfigured ? 6 : 0}
              required={isSupabaseConfigured}
            />
          </div>

          <button className="auth-submit large" type="submit" disabled={loading}>
            {loading ? <LoaderCircle size={17} className="spin" /> : null}
            {isRegister ? "Register" : "Login"}
          </button>
          {status && <p className="auth-feedback">{status}</p>}
        </form>

        <button className="auth-switch" type="button" onClick={() => onModeChange(isRegister ? "login" : "register")}>
          {isRegister ? "Sudah punya akun? Login" : "Belum punya akun? Register"}
        </button>
      </section>
    </main>
  );
}

function ChatSidebar({
  apiStatus,
  checkHealth,
  threads,
  activeThreadId,
  onNewChat,
  onOpenThread,
  onDeleteThread,
  onSignOut,
  session,
  demoUser,
}) {
  return (
    <aside className="chat-sidebar" aria-label="Sidebar chat history">
      <div className="sidebar-brand">
        <a className="brand" href="#top" aria-label="CineMatch home">
          <span className="brand-mark"><Clapperboard size={20} /></span>
          <span>CineMatch</span>
        </a>
      </div>

      <button className="new-chat-button" type="button" onClick={onNewChat}>
        <Plus size={16} /> Chat baru / cari movie lain
      </button>

      <div className="sidebar-section-title">
        <History size={14} />
        <span>History per movie</span>
      </div>

      <div className="sidebar-thread-list">
        {threads.length > 0 ? threads.map((thread) => (
          <div className={`sidebar-thread ${thread.id === activeThreadId ? "active" : ""}`} key={thread.id}>
            <button type="button" onClick={() => onOpenThread(thread.id)}>
              <span className="mini-poster">
                {thread.movie.poster_path
                  ? <img src={`https://image.tmdb.org/t/p/w185${thread.movie.poster_path}`} alt="" />
                  : <Film size={16} />}
              </span>
              <span className="thread-label">
                <strong>{thread.movie.title}</strong>
                <small>{thread.messages.length} pesan · {formatThreadTime(thread.updated_at)}</small>
              </span>
            </button>
            <button
              className="delete-thread"
              type="button"
              onClick={(event) => {
                event.preventDefault();
                event.stopPropagation();
                onDeleteThread(thread.id);
              }}
              aria-label={`Hapus chat ${thread.movie.title}`}
            >
              <Trash2 size={14} />
            </button>
          </div>
        )) : (
          <div className="sidebar-empty">
            <Film size={26} />
            <p>Belum ada chat movie. Klik salah satu movie untuk membuat thread.</p>
          </div>
        )}
      </div>

      <div className="sidebar-footer">
        <div className={`api-status ${apiStatus}`}>
          {apiStatus === "online" && <CheckCircle2 size={15} />}
          {apiStatus === "checking" && <LoaderCircle size={15} className="spin" />}
          {apiStatus === "offline" && <WifiOff size={15} />}
          <span>
            {apiStatus === "online" ? "Engine online" : null}
            {apiStatus === "checking" ? "Checking" : null}
            {apiStatus === "offline" ? "Engine offline" : null}
          </span>
          {apiStatus === "offline" && (
            <button type="button" onClick={checkHealth} title="Coba hubungkan kembali">
              <RefreshCw size={14} />
            </button>
          )}
        </div>
        <div className="user-chip">
          <UserRound size={15} />
          <span>{userLabel(session, demoUser)}</span>
        </div>
        <button className="signout-button" type="button" onClick={onSignOut}>
          <LogOut size={15} /> Logout
        </button>
      </div>
    </aside>
  );
}

function RecommendationChat({
  messages,
  candidates,
  loading,
  error,
  input,
  setInput,
  onSubmit,
  onSuggestion,
  onSelectCandidate,
  llmStatus,
  messagesEndRef,
}) {
  return (
    <section className="context-chat-card" aria-label="Movie recommendation chat">
      <div className="context-chat-heading">
        <span
          className="eyebrow"
          title={llmStatus.enabled ? `OpenAI model: ${llmStatus.model}` : "OpenAI belum dikonfigurasi"}
        >
          <Sparkles size={15} />
          {llmStatus.enabled ? "OpenAI + Word2Vec + Qdrant" : "Word2Vec + Qdrant (fallback)"}
        </span>
        <h1>Rekomendasi film</h1>
        <p>Ketik film acuan atau filter. Setelah hasil muncul, klik movie untuk mengunci chat ke movie tersebut.</p>
      </div>

      <div className="messages context-messages" aria-live="polite">
        {messages.map((message) => (
          <div className={`message ${message.role}`} key={message.id}>
            <span className="avatar">
              {message.role === "assistant" ? <Bot size={17} /> : <UserRound size={17} />}
            </span>
            <p>{message.content}</p>
          </div>
        ))}

        {loading && (
          <div className="message assistant thinking">
            <span className="avatar"><Bot size={17} /></span>
            <p><span /><span /><span /></p>
          </div>
        )}

        {candidates.length > 0 && (
          <div className="candidate-list">
            {candidates.map((movie) => (
              <button type="button" key={movie.id} onClick={() => onSelectCandidate(movie)}>
                <Search size={15} />
                <span>{movie.title}</span>
                <small>{movie.release_year || "-"}</small>
              </button>
            ))}
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {messages.length === 1 && (
        <div className="suggestions">
          {(llmStatus.enabled ? LLM_SUGGESTIONS : SUGGESTIONS).map((suggestion) => (
            <button type="button" key={suggestion} onClick={() => onSuggestion(suggestion)}>
              {suggestion}
            </button>
          ))}
        </div>
      )}

      {error && <p className="error-banner">{error}</p>}

      <form className="composer sticky-composer" onSubmit={onSubmit}>
        <label htmlFor="movie-query" className="sr-only">Film yang kamu sukai</label>
        <input
          id="movie-query"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="Contoh: Film seperti Interstellar"
          autoComplete="off"
        />
        <button type="submit" disabled={!input.trim() || loading} aria-label="Kirim permintaan">
          {loading ? <LoaderCircle size={19} className="spin" /> : <ArrowUp size={19} />}
        </button>
      </form>
    </section>
  );
}

export default function App() {
  const [initialWorkspace] = useState(loadWorkspace);
  const [view, setView] = useState(() => localStorage.getItem(ENTRY_STORAGE_KEY) || "landing");
  const [authMode, setAuthMode] = useState("login");
  const [session, setSession] = useState(null);
  const [demoUser, setDemoUser] = useState(loadDemoUser);
  const [messages, setMessages] = useState(initialWorkspace.messages || INITIAL_MESSAGES);
  const [input, setInput] = useState("");
  const [recommendations, setRecommendations] = useState(initialWorkspace.recommendations || []);
  const [source, setSource] = useState(initialWorkspace.source || null);
  const [candidates, setCandidates] = useState([]);
  const [loading, setLoading] = useState(false);
  const [apiStatus, setApiStatus] = useState("checking");
  const [llmStatus, setLlmStatus] = useState({ enabled: false, model: null });
  const [queryAnalysis, setQueryAnalysis] = useState(initialWorkspace.queryAnalysis || null);
  const [error, setError] = useState("");
  const [rootThreadId, setRootThreadId] = useState(initialWorkspace.rootThreadId || createId);
  const [movieThreads, setMovieThreads] = useState(loadLocalThreads);
  const [activeMovieThreadId, setActiveMovieThreadId] = useState(initialWorkspace.activeMovieThreadId || null);
  const [movieThreadLoading, setMovieThreadLoading] = useState(false);
  const [catalogLoading, setCatalogLoading] = useState(false);
  const [chatOpen, setChatOpen] = useState(true);
  const [selectedMovieDetail, setSelectedMovieDetail] = useState(null);
  const messagesEndRef = useRef(null);
  const activeMovieThread = movieThreads.find((thread) => thread.id === activeMovieThreadId) || null;
  const sortedMovieThreads = useMemo(
    () => [...movieThreads].sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at)),
    [movieThreads],
  );

  const authenticated = Boolean(session || demoUser);

  useEffect(() => {
    checkHealth();
  }, []);

  useEffect(() => {
    if (!supabase) return undefined;

    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      if (data.session && localStorage.getItem(ENTRY_STORAGE_KEY) === "app") {
        setView("app");
      }
    });
    const { data: listener } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession);
      if (nextSession) {
        localStorage.setItem(ENTRY_STORAGE_KEY, "app");
        setView("app");
      }
    });
    return () => listener.subscription.unsubscribe();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, candidates, loading]);

  useEffect(() => {
    localStorage.setItem(WORKSPACE_STORAGE_KEY, JSON.stringify({
      rootThreadId,
      messages,
      recommendations,
      source,
      queryAnalysis,
      activeMovieThreadId,
    }));
  }, [rootThreadId, messages, recommendations, source, queryAnalysis, activeMovieThreadId]);

  useEffect(() => {
    saveLocalThreads(movieThreads);
    if (!session?.user?.id) return;
    movieThreads.forEach((thread) => {
      syncThreadToSupabase(thread, session.user.id).catch(() => undefined);
    });
  }, [movieThreads, session]);

  useEffect(() => {
    if (!session?.user?.id) return;
    loadRemoteMovieThreads(session.user.id)
      .then((remoteThreads) => setMovieThreads((localThreads) => mergeThreads(localThreads, remoteThreads)))
      .catch(() => undefined);
  }, [session]);

  useEffect(() => {
    if (!authenticated) return;
    if (recommendations.length > 0 || source || activeMovieThread) return;
    loadDefaultMovies();
  }, [authenticated]);

  const openAuth = useCallback((mode) => {
    setAuthMode(mode);
    setView("auth");
  }, []);

  async function checkHealth() {
    setApiStatus("checking");
    try {
      const response = await fetch(`${API_BASE_URL}/health`);
      if (!response.ok) throw new Error("API tidak tersedia");
      const data = await response.json();
      setLlmStatus({
        enabled: Boolean(data.llm?.enabled),
        model: data.llm?.model || null,
      });
      setApiStatus("online");
    } catch {
      setLlmStatus({ enabled: false, model: null });
      setApiStatus("offline");
    }
  }

  async function loadDefaultMovies() {
    setCatalogLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/movies?limit=12`);
      if (!response.ok) throw new Error("Catalog movie tidak tersedia.");
      const data = await response.json();
      setSource(null);
      setRecommendations(data.results || []);
    } catch {
      setRecommendations((current) => current);
    } finally {
      setCatalogLoading(false);
    }
  }

  function addMessage(role, content) {
    setMessages((current) => [
      ...current,
      { id: `${Date.now()}-${Math.random()}`, role, content },
    ]);
  }

  function startNewChat() {
    const nextRootId = createId();
    setRootThreadId(nextRootId);
    setActiveMovieThreadId(null);
    setMessages(INITIAL_MESSAGES);
    setInput("");
    setCandidates([]);
    setError("");
    setSource(null);
    setRecommendations([]);
    setQueryAnalysis(null);
    setSelectedMovieDetail(null);
    setChatOpen(true);
    loadDefaultMovies();
  }

  async function requestRecommendations(message) {
    const cleanMessage = message.trim();
    if (!cleanMessage || loading) return;

    setActiveMovieThreadId(null);
    setSelectedMovieDetail(null);
    setInput("");
    setError("");
    setCandidates([]);
    setQueryAnalysis(null);
    addMessage("user", cleanMessage);
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: cleanMessage, top_k: 8 }),
      });

      if (!response.ok) {
        const detail = await response.json().catch(() => ({}));
        throw new Error(detail.detail || "Backend tidak dapat memproses permintaan.");
      }

      const data = await response.json();
      addMessage("assistant", data.message);
      setQueryAnalysis(data.query_analysis || null);

      if (data.status === "recommendations") {
        setSource(data.source);
        setRecommendations(data.recommendations);
      } else {
        setCandidates(data.candidates || []);
        if (data.status === "not_found") {
          setSource(null);
          setRecommendations((current) => {
            if (current.length === 0) loadDefaultMovies();
            return current;
          });
        }
      }
    } catch (requestError) {
      setError(requestError.message);
      addMessage(
        "assistant",
        "Koneksi ke layanan rekomendasi terganggu. Pastikan backend dan Qdrant sedang berjalan.",
      );
      setApiStatus("offline");
      setQueryAnalysis(null);
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(event) {
    event.preventDefault();
    requestRecommendations(input);
  }

  function selectCandidate(movie) {
    requestRecommendations(`Saya ingin film seperti ${movie.title}`);
  }

  function openMovieThread(movie) {
    setSelectedMovieDetail(movie);
    const existing = movieThreads.find((thread) => thread.movie.id === movie.id);
    if (existing) {
      setActiveMovieThreadId(existing.id);
      setChatOpen(true);
      return;
    }

    const now = new Date().toISOString();
    const welcomeMessage = {
      id: createId(),
      role: "assistant",
      content: `Chat sekarang dikunci ke ${movie.title}. Tanya apa pun tentang movie ini: sinopsis, pemain, sutradara, genre, rating, atau alasan rekomendasi.`,
      parent_message_id: null,
      metadata: { kind: "thread_created" },
      created_at: now,
    };
    const thread = {
      id: createId(),
      parent_thread_id: rootThreadId,
      movie,
      title: movie.title,
      messages: [welcomeMessage],
      created_at: now,
      updated_at: now,
    };
    setMovieThreads((current) => [thread, ...current]);
    setActiveMovieThreadId(thread.id);
    setChatOpen(true);
  }

  function openSavedThread(threadId) {
    const savedThread = movieThreads.find((thread) => thread.id === threadId);
    setActiveMovieThreadId(threadId);
    setSelectedMovieDetail(savedThread?.movie || null);
    setChatOpen(true);
  }

  async function deleteThread(threadId) {
    const threadToDelete = movieThreads.find((thread) => thread.id === threadId);
    const remainingThreads = movieThreads.filter((thread) => thread.id !== threadId);
    setMovieThreads(remainingThreads);

    if (activeMovieThreadId === threadId) {
      const nextThread = remainingThreads[0] || null;
      setActiveMovieThreadId(nextThread?.id || null);
      setSelectedMovieDetail(nextThread?.movie || null);
      setChatOpen(Boolean(nextThread));
    } else if (threadToDelete && selectedMovieDetail?.id === threadToDelete.movie.id) {
      setSelectedMovieDetail(null);
    }

    if (session?.user?.id) {
      deleteRemoteThread(threadId, session.user.id).catch(() => undefined);
    }
  }

  async function sendMovieQuestion(content) {
    const thread = movieThreads.find((item) => item.id === activeMovieThreadId);
    if (!thread || movieThreadLoading) return;

    const now = new Date().toISOString();
    const parentMessage = thread.messages.at(-1);
    const userMessage = {
      id: createId(),
      role: "user",
      content,
      parent_message_id: parentMessage?.id || null,
      metadata: {},
      created_at: now,
    };
    setMovieThreads((current) => current.map((item) => item.id === thread.id
      ? { ...item, messages: [...item.messages, userMessage], updated_at: now }
      : item));
    setMovieThreadLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/movies/${thread.movie.id}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: content,
          history: thread.messages.map(({ role, content: historyContent }) => ({
            role,
            content: historyContent,
          })),
        }),
      });
      if (!response.ok) {
        const detail = await response.json().catch(() => ({}));
        throw new Error(detail.detail || "Pertanyaan lanjutan gagal diproses.");
      }
      const data = await response.json();
      const assistantMessage = {
        id: createId(),
        role: "assistant",
        content: data.answer,
        parent_message_id: userMessage.id,
        metadata: { llm_used: data.llm_used, llm_model: data.llm_model },
        created_at: new Date().toISOString(),
      };
      setMovieThreads((current) => current.map((item) => item.id === thread.id
        ? {
            ...item,
            messages: [...item.messages, assistantMessage],
            updated_at: assistantMessage.created_at,
          }
        : item));
    } catch (followUpError) {
      const errorMessage = {
        id: createId(),
        role: "assistant",
        content: `Maaf, pertanyaan ini belum bisa dijawab: ${followUpError.message}`,
        parent_message_id: userMessage.id,
        metadata: { error: true },
        created_at: new Date().toISOString(),
      };
      setMovieThreads((current) => current.map((item) => item.id === thread.id
        ? { ...item, messages: [...item.messages, errorMessage], updated_at: errorMessage.created_at }
        : item));
    } finally {
      setMovieThreadLoading(false);
    }
  }

  async function signOut() {
    if (supabase && session) await supabase.auth.signOut();
    localStorage.removeItem(DEMO_USER_STORAGE_KEY);
    localStorage.removeItem(ENTRY_STORAGE_KEY);
    setSession(null);
    setDemoUser(null);
    setView("landing");
  }

  if (view === "landing" || !authenticated) {
    if (view === "auth") {
      return (
        <AuthPage
          mode={authMode}
          onModeChange={setAuthMode}
          onBack={() => setView("landing")}
          onAuthenticated={({ session: nextSession, demoUser: nextDemoUser }) => {
            if (nextSession) setSession(nextSession);
            if (nextDemoUser) setDemoUser(nextDemoUser);
            setView("app");
          }}
        />
      );
    }

    return <LandingPage onLogin={() => openAuth("login")} onRegister={() => openAuth("register")} />;
  }

  return (
    <main className="app-shell app-workspace" id="top">
      <ChatSidebar
        apiStatus={apiStatus}
        checkHealth={checkHealth}
        threads={sortedMovieThreads}
        activeThreadId={activeMovieThreadId}
        onNewChat={startNewChat}
        onOpenThread={openSavedThread}
        onDeleteThread={deleteThread}
        onSignOut={signOut}
        session={session}
        demoUser={demoUser}
      />

      <section className="main-stage">
        <header className="stage-topbar">
          <div>
            <span className="section-number">/ CURRENT MODE</span>
            <h2>{activeMovieThread ? `Chat: ${activeMovieThread.movie.title}` : "Movie discovery"}</h2>
          </div>
          <div className="stage-actions">
            <button className="chat-toggle-button" type="button" onClick={() => setChatOpen((value) => !value)}>
              {chatOpen ? <X size={15} /> : <MessageCircleMore size={15} />}
              {chatOpen ? "Tutup chat" : "Buka chat"}
            </button>
            <QueryAnalysisDrawer analysis={queryAnalysis} />
          </div>
        </header>

        <div className={`stage-grid ${chatOpen ? "" : "chat-collapsed"}`}>
          {chatOpen && (
            <div className="stage-chat-column">
              {activeMovieThread ? (
                <MovieConversation
                  thread={activeMovieThread}
                  loading={movieThreadLoading}
                  onClose={() => setActiveMovieThreadId(null)}
                  onSend={sendMovieQuestion}
                  embedded
                />
              ) : (
                <RecommendationChat
                  messages={messages}
                  candidates={candidates}
                  loading={loading}
                  error={error}
                  input={input}
                  setInput={setInput}
                  onSubmit={handleSubmit}
                  onSuggestion={requestRecommendations}
                  onSelectCandidate={selectCandidate}
                  llmStatus={llmStatus}
                  messagesEndRef={messagesEndRef}
                />
              )}
            </div>
          )}

          <section className="results-panel compact-results" aria-label="Movie recommendations">
            <div className="results-heading">
              <div>
                <span className="section-number">/ MOVIES</span>
                <h2>
                  {activeMovieThread && recommendations.length === 0
                    ? "Movie yang sedang dibahas"
                    : source
                    ? `Because you liked ${source.title}`
                    : recommendations.length > 0 && queryAnalysis?.execution_mode === "discovery"
                      ? "Matches your filters"
                      : recommendations.length > 0
                        ? "Movie list"
                      : "Movie list"}
                </h2>
              </div>
              {source && (
                <div className="source-chip">
                  <Clapperboard size={15} />
                  {source.release_year} · {source.genres}
                </div>
              )}
            </div>

            {(loading || catalogLoading) && <SkeletonGrid />}

            {!loading && !catalogLoading && selectedMovieDetail && (
              <MovieDetailPanel
                movie={selectedMovieDetail}
                onBack={() => setSelectedMovieDetail(null)}
                onDiscuss={openMovieThread}
              />
            )}

            {!loading && !catalogLoading && !selectedMovieDetail && activeMovieThread && recommendations.length === 0 && (
              <LockedMovieSummary thread={activeMovieThread} />
            )}

            {!loading && !catalogLoading && !selectedMovieDetail && recommendations.length > 0 && (
              <div className="recommendation-grid">
                {recommendations.map((movie, index) => (
                  <RecommendationCard
                    movie={movie}
                    index={index}
                    key={movie.id}
                    onDiscuss={openMovieThread}
                  />
                ))}
              </div>
            )}

            {!loading && !catalogLoading && !selectedMovieDetail && !activeMovieThread && recommendations.length === 0 && (
              <div className="empty-state">
                <div className="film-frame"><Film size={44} strokeWidth={1.25} /></div>
                <h3>Belum ada movie list</h3>
                <p>Gunakan chat rekomendasi di kiri untuk mencari film, lalu klik salah satu movie agar chat terkunci ke film itu.</p>
              </div>
            )}
          </section>
        </div>
      </section>
    </main>
  );
}
