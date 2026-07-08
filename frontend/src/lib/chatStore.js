import { isSupabaseConfigured, supabase } from "./supabase";

const THREAD_STORAGE_KEY = "cinematch:movie-threads:v1";

export function createId() {
  return globalThis.crypto?.randomUUID?.()
    || `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function loadLocalThreads() {
  try {
    const stored = JSON.parse(localStorage.getItem(THREAD_STORAGE_KEY) || "[]");
    return Array.isArray(stored) ? stored : [];
  } catch {
    return [];
  }
}

export function saveLocalThreads(threads) {
  localStorage.setItem(THREAD_STORAGE_KEY, JSON.stringify(threads));
}

export function mergeThreads(localThreads, remoteThreads) {
  const merged = new Map();
  [...localThreads, ...remoteThreads].forEach((thread) => {
    const current = merged.get(thread.id);
    if (!current || new Date(thread.updated_at) >= new Date(current.updated_at)) {
      merged.set(thread.id, thread);
    }
  });
  return [...merged.values()].sort(
    (a, b) => new Date(b.updated_at) - new Date(a.updated_at),
  );
}

export async function ensureRemoteRootThread(rootThreadId, userId) {
  if (!isSupabaseConfigured || !userId) return;
  const { error } = await supabase.from("chat_threads").upsert({
    id: rootThreadId,
    user_id: userId,
    parent_thread_id: null,
    context_type: "recommendation",
    title: "Movie recommendations",
    updated_at: new Date().toISOString(),
  });
  if (error) throw error;
}

export async function syncThreadToSupabase(thread, userId) {
  if (!isSupabaseConfigured || !userId) return;

  await ensureRemoteRootThread(thread.parent_thread_id, userId);
  const { error: threadError } = await supabase.from("chat_threads").upsert({
    id: thread.id,
    user_id: userId,
    parent_thread_id: thread.parent_thread_id,
    context_type: "movie",
    context_movie_id: thread.movie.id,
    context_movie: thread.movie,
    title: thread.title,
    created_at: thread.created_at,
    updated_at: thread.updated_at,
  });
  if (threadError) throw threadError;

  if (thread.messages.length > 0) {
    const rows = thread.messages.map((message) => ({
      id: message.id,
      thread_id: thread.id,
      user_id: userId,
      parent_message_id: message.parent_message_id || null,
      role: message.role,
      content: message.content,
      metadata: message.metadata || {},
      created_at: message.created_at,
    }));
    const { error: messageError } = await supabase.from("chat_messages").upsert(rows);
    if (messageError) throw messageError;
  }
}

export async function loadRemoteMovieThreads(userId) {
  if (!isSupabaseConfigured || !userId) return [];

  const { data: threads, error: threadError } = await supabase
    .from("chat_threads")
    .select("*")
    .eq("user_id", userId)
    .eq("context_type", "movie")
    .order("updated_at", { ascending: false });
  if (threadError) throw threadError;
  if (!threads?.length) return [];

  const threadIds = threads.map((thread) => thread.id);
  const { data: messages, error: messageError } = await supabase
    .from("chat_messages")
    .select("*")
    .in("thread_id", threadIds)
    .order("created_at", { ascending: true });
  if (messageError) throw messageError;

  return threads.map((thread) => ({
    id: thread.id,
    parent_thread_id: thread.parent_thread_id,
    movie: thread.context_movie,
    title: thread.title,
    created_at: thread.created_at,
    updated_at: thread.updated_at,
    messages: (messages || [])
      .filter((message) => message.thread_id === thread.id)
      .map((message) => ({
        id: message.id,
        role: message.role,
        content: message.content,
        parent_message_id: message.parent_message_id,
        metadata: message.metadata,
        created_at: message.created_at,
      })),
  }));
}

export async function deleteRemoteThread(threadId, userId) {
  if (!isSupabaseConfigured || !userId) return;

  const { error } = await supabase
    .from("chat_threads")
    .delete()
    .eq("id", threadId)
    .eq("user_id", userId);
  if (error) throw error;
}
