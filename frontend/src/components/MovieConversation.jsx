import { useEffect, useRef, useState } from "react";
import { ArrowUp, Bot, ChevronRight, Film, LoaderCircle, MessageCircleMore, Star, UserRound, X } from "lucide-react";

const QUESTION_STARTERS = [
  "Ceritanya tentang apa?",
  "Siapa sutradara dan pemain utamanya?",
  "Kenapa film ini direkomendasikan?",
];

export default function MovieConversation({ thread, loading, onClose, onSend, embedded = false }) {
  const [input, setInput] = useState("");
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [thread?.messages, loading]);

  if (!thread) return null;
  const movie = thread.movie;

  function submit(event) {
    event.preventDefault();
    if (!input.trim() || loading) return;
    onSend(input.trim());
    setInput("");
  }

  return (
    <aside className={`movie-thread ${embedded ? "embedded-thread" : ""}`} aria-label={`Diskusi tentang ${movie.title}`}>
      <header className="movie-thread-header">
        <div className="thread-breadcrumb">
          <span>Movie context</span><ChevronRight size={12} /><strong>Locked chat</strong>
        </div>
        <button type="button" onClick={onClose} aria-label="Kembali ke rekomendasi"><X size={18} /></button>
      </header>

      <div className="thread-movie-context">
        <div className="thread-poster">
          {movie.poster_path
            ? <img src={`https://image.tmdb.org/t/p/w342${movie.poster_path}`} alt={`Poster ${movie.title}`} />
            : <Film size={28} />}
        </div>
        <div>
          <span className="context-kicker"><MessageCircleMore size={13} /> Context locked</span>
          <h2>{movie.title}</h2>
          <p>{[movie.release_year, movie.genres, movie.runtime && `${movie.runtime} min`].filter(Boolean).join(" · ")}</p>
          <span className="context-rating"><Star size={13} fill="currentColor" /> {movie.vote_average?.toFixed(1) || "-"}</span>
        </div>
      </div>

      <div className="thread-messages" aria-live="polite">
        {thread.messages.map((message) => (
          <div className={`thread-message ${message.role}`} key={message.id}>
            <span>{message.role === "assistant" ? <Bot size={15} /> : <UserRound size={15} />}</span>
            <p>{message.content}</p>
          </div>
        ))}
        {loading && (
          <div className="thread-message assistant">
            <span><Bot size={15} /></span>
            <p className="thread-thinking"><i /><i /><i /></p>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {thread.messages.length <= 1 && (
        <div className="thread-starters">
          {QUESTION_STARTERS.map((question) => (
            <button type="button" key={question} onClick={() => onSend(question)}>{question}</button>
          ))}
        </div>
      )}

      <form className="thread-composer sticky-composer" onSubmit={submit}>
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder={`Tanya lebih lanjut tentang ${movie.title}`}
          aria-label={`Pertanyaan tentang ${movie.title}`}
        />
        <button type="submit" disabled={!input.trim() || loading}>
          {loading ? <LoaderCircle size={17} className="spin" /> : <ArrowUp size={17} />}
        </button>
      </form>
    </aside>
  );
}
