import { useEffect, useRef, useState } from "react";
import {
  ArrowUp,
  Bot,
  Braces,
  BrainCircuit,
  CheckCircle2,
  ChevronDown,
  Clapperboard,
  Database,
  Film,
  LoaderCircle,
  RefreshCw,
  Search,
  Sparkles,
  Star,
  UserRound,
  WifiOff,
  Workflow,
} from "lucide-react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const POSTER_BASE_URL = "https://image.tmdb.org/t/p/w500";

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
      "Sebutkan film yang kamu suka. Aku akan mencari judulnya lalu menampilkan film dengan karakter paling mirip.",
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

function QueryAnalysisPanel({ analysis }) {
  if (!analysis) return null;

  const intentEntries = detectedIntentEntries(analysis.extracted_intent);
  const parameters = analysis.execution_parameters || {};
  const modeLabel = {
    similarity: "Similarity search",
    discovery: "Metadata discovery",
    clarification: "Clarification",
  }[analysis.execution_mode];

  return (
    <section className="query-trace" aria-label="Analisis dan eksekusi query">
      <div className="trace-header">
        <div>
          <span className="trace-overline"><Workflow size={13} /> Query trace</span>
          <h3>Bagaimana sistem membaca permintaan ini</h3>
        </div>
        <div className="trace-badges">
          <span>{analysis.interpreter === "openai" ? "OpenAI intent parser" : "Fallback parser"}</span>
          <strong>{modeLabel}</strong>
        </div>
      </div>

      <div className="trace-grid">
        <article className="trace-stage intent-stage">
          <div className="stage-number">01</div>
          <div className="stage-copy">
            <div className="stage-title"><BrainCircuit size={16} /> Yang diambil dari query</div>
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
            <p className="stage-note">LLM tidak mengeksekusi database; backend menjalankan pipeline berikut.</p>
            <code className="backend-query">{analysis.backend_query}</code>
            <div className="execution-facts">
              {parameters.qdrant_collection && <span>Collection <strong>{parameters.qdrant_collection}</strong></span>}
              {parameters.candidate_pool_target && <span>Candidate pool <strong>{parameters.candidate_pool_target}</strong></span>}
              {parameters.top_k && <span>Final top-k <strong>{parameters.top_k}</strong></span>}
            </div>
          </div>
        </article>
      </div>

      <ol className="execution-steps">
        {analysis.steps.map((step, index) => (
          <li key={`${index}-${step}`}><span>{index + 1}</span><p>{step}</p></li>
        ))}
      </ol>

      <details className="raw-intent">
        <summary><Braces size={14} /> Lihat raw structured intent <ChevronDown size={14} /></summary>
        <pre>{JSON.stringify(analysis.extracted_intent, null, 2)}</pre>
      </details>
    </section>
  );
}

function posterUrl(path) {
  return path ? `${POSTER_BASE_URL}${path}` : null;
}

function formatScore(value) {
  return typeof value === "number" ? `${Math.round(value * 100)}%` : "-";
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

function RecommendationCard({ movie, index }) {
  const displayedScore = movie.score_type === "discovery"
    ? movie.hybrid_score
    : movie.similarity_score;
  const scoreLabel = movie.score_type === "discovery"
    ? "Discovery score"
    : "Content match";

  return (
    <article className="movie-card" style={{ "--delay": `${index * 55}ms` }}>
      <div className="poster-wrap">
        <MoviePoster movie={movie} priority={index < 2} />
        <span className="rank">{String(index + 1).padStart(2, "0")}</span>
      </div>
      <div className="movie-copy">
        <div className="movie-heading">
          <div>
            <h3>{movie.title}</h3>
            <p>{movie.release_year || "Tahun tidak tersedia"}</p>
          </div>
          <div className="rating" title="TMDB vote average">
            <Star size={14} fill="currentColor" />
            {movie.vote_average?.toFixed(1) || "-"}
          </div>
        </div>

        <p className="genres">{movie.genres || "Genre tidak tersedia"}</p>
        <p className="movie-facts">
          {[movie.original_language?.toUpperCase(), movie.runtime && `${movie.runtime} min`, movie.director]
            .filter(Boolean)
            .join(" · ") || "Metadata tambahan tidak tersedia"}
        </p>
        {movie.cast && <p className="cast-line">Cast: {movie.cast}</p>}
        <p className="reason">{movie.reason}</p>
        {movie.overview && <p className="overview">{movie.overview}</p>}

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

export default function App() {
  const [messages, setMessages] = useState(INITIAL_MESSAGES);
  const [input, setInput] = useState("");
  const [recommendations, setRecommendations] = useState([]);
  const [source, setSource] = useState(null);
  const [candidates, setCandidates] = useState([]);
  const [loading, setLoading] = useState(false);
  const [apiStatus, setApiStatus] = useState("checking");
  const [llmStatus, setLlmStatus] = useState({ enabled: false, model: null });
  const [queryAnalysis, setQueryAnalysis] = useState(null);
  const [error, setError] = useState("");
  const messagesEndRef = useRef(null);

  useEffect(() => {
    checkHealth();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, candidates, loading]);

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

  function addMessage(role, content) {
    setMessages((current) => [
      ...current,
      { id: `${Date.now()}-${Math.random()}`, role, content },
    ]);
  }

  async function requestRecommendations(message) {
    const cleanMessage = message.trim();
    if (!cleanMessage || loading) return;

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
          setRecommendations([]);
          setSource(null);
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

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="CineMatch home">
          <span className="brand-mark"><Clapperboard size={22} /></span>
          <span>CineMatch</span>
        </a>

        <div className={`api-status ${apiStatus}`}>
          {apiStatus === "online" && <CheckCircle2 size={15} />}
          {apiStatus === "checking" && <LoaderCircle size={15} className="spin" />}
          {apiStatus === "offline" && <WifiOff size={15} />}
          <span>
            {apiStatus === "online" ? "Recommendation engine online" : null}
            {apiStatus === "checking" ? "Checking engine" : null}
            {apiStatus === "offline" ? "Engine offline" : null}
          </span>
          {apiStatus === "offline" && (
            <button type="button" onClick={checkHealth} title="Coba hubungkan kembali">
              <RefreshCw size={14} />
            </button>
          )}
        </div>
      </header>

      <section className="workspace" id="top">
        <section className="chat-panel" aria-label="Movie recommendation chat">
          <div className="chat-heading">
            <span
              className="eyebrow"
              title={llmStatus.enabled ? `OpenAI model: ${llmStatus.model}` : "OpenAI belum dikonfigurasi"}
            >
              <Sparkles size={15} />
              {llmStatus.enabled ? "OpenAI + Word2Vec + Qdrant" : "Word2Vec + Qdrant (fallback)"}
            </span>
            <h1>What should we watch next?</h1>
            <p>Mulai dari satu film yang kamu suka.</p>
          </div>

          <div className="messages" aria-live="polite">
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
                  <button type="button" key={movie.id} onClick={() => selectCandidate(movie)}>
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
                <button type="button" key={suggestion} onClick={() => requestRecommendations(suggestion)}>
                  {suggestion}
                </button>
              ))}
            </div>
          )}

          {error && <p className="error-banner">{error}</p>}

          <form className="composer" onSubmit={handleSubmit}>
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

        <section className="results-panel" aria-label="Movie recommendations">
          <div className="results-heading">
            <div>
              <span className="section-number">/ 01</span>
              <h2>
                {source
                  ? `Because you liked ${source.title}`
                  : recommendations.length > 0
                    ? "Matches your filters"
                    : "Your next watchlist"}
              </h2>
            </div>
            {source && (
              <div className="source-chip">
                <Clapperboard size={15} />
                {source.release_year} · {source.genres}
              </div>
            )}
          </div>

          <QueryAnalysisPanel analysis={queryAnalysis} />

          {loading && <SkeletonGrid />}

          {!loading && recommendations.length > 0 && (
            <div className="recommendation-grid">
              {recommendations.map((movie, index) => (
                <RecommendationCard movie={movie} index={index} key={movie.id} />
              ))}
            </div>
          )}

          {!loading && recommendations.length === 0 && (
            <div className="empty-state">
              <div className="film-frame"><Film size={44} strokeWidth={1.25} /></div>
              <h3>No titles on the reel yet</h3>
              <p>Rekomendasi akan muncul di sini setelah kamu memilih film acuan.</p>
            </div>
          )}
        </section>
      </section>
    </main>
  );
}
