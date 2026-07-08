import { Clock3, Film, MessageCircleMore, X } from "lucide-react";

function formatThreadTime(value) {
  return new Intl.DateTimeFormat("id-ID", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export default function HistoryDrawer({ open, threads, onClose, onOpenThread }) {
  if (!open) return null;

  return (
    <aside className="history-drawer" aria-label="Riwayat diskusi film">
      <div className="drawer-heading">
        <div>
          <span><Clock3 size={14} /> Conversation archive</span>
          <h2>Movie threads</h2>
        </div>
        <button type="button" onClick={onClose} aria-label="Tutup riwayat"><X size={18} /></button>
      </div>

      <p className="drawer-description">
        Setiap film memiliki thread turunan sendiri, sehingga context antarfim tidak tercampur.
      </p>

      <div className="thread-list">
        {threads.length > 0 ? threads.map((thread) => (
          <button type="button" className="thread-history-card" key={thread.id} onClick={() => onOpenThread(thread.id)}>
            <span className="history-poster">
              {thread.movie.poster_path
                ? <img src={`https://image.tmdb.org/t/p/w185${thread.movie.poster_path}`} alt="" />
                : <Film size={20} />}
            </span>
            <span className="history-copy">
              <strong>{thread.movie.title}</strong>
              <small>{thread.messages.length} pesan · {formatThreadTime(thread.updated_at)}</small>
              <em>{thread.messages.at(-1)?.content || "Thread baru"}</em>
            </span>
            <MessageCircleMore size={16} />
          </button>
        )) : (
          <div className="history-empty">
            <Film size={30} />
            <strong>Belum ada movie thread</strong>
            <p>Tekan “Tanya tentang film ini” pada salah satu rekomendasi.</p>
          </div>
        )}
      </div>
    </aside>
  );
}
