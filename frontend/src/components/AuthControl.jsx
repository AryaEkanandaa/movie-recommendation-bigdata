import { useEffect, useState } from "react";
import { HardDrive, LogIn, LogOut, Mail, UserRound, X } from "lucide-react";

import { isSupabaseConfigured, supabase } from "../lib/supabase";

export default function AuthControl({ onSessionChange }) {
  const [session, setSession] = useState(null);
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!supabase) return undefined;

    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      onSessionChange?.(data.session);
    });
    const { data: listener } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession);
      onSessionChange?.(nextSession);
    });
    return () => listener.subscription.unsubscribe();
  }, [onSessionChange]);

  async function sendMagicLink(event) {
    event.preventDefault();
    if (!email.trim()) return;
    setLoading(true);
    setStatus("");
    const { error } = await supabase.auth.signInWithOtp({
      email: email.trim(),
      options: { emailRedirectTo: window.location.origin },
    });
    setStatus(error ? error.message : "Magic link sudah dikirim. Periksa email kamu.");
    setLoading(false);
  }

  async function signOut() {
    await supabase.auth.signOut();
    setOpen(false);
  }

  if (!isSupabaseConfigured) {
    return (
      <span className="persistence-status" title="History disimpan pada browser ini">
        <HardDrive size={14} /> Local history
      </span>
    );
  }

  return (
    <div className="auth-control">
      <button className="auth-trigger" type="button" onClick={() => setOpen((value) => !value)}>
        {session ? <UserRound size={15} /> : <LogIn size={15} />}
        <span>{session?.user?.email || "Sign in"}</span>
      </button>

      {open && (
        <div className="auth-popover">
          <button className="popover-close" type="button" onClick={() => setOpen(false)} aria-label="Tutup">
            <X size={14} />
          </button>
          {session ? (
            <>
              <span className="auth-kicker">Synced history</span>
              <h3>Welcome back</h3>
              <p>Nested movie threads disinkronkan ke akun Supabase ini.</p>
              <strong>{session.user.email}</strong>
              <button className="auth-submit secondary" type="button" onClick={signOut}>
                <LogOut size={14} /> Sign out
              </button>
            </>
          ) : (
            <form onSubmit={sendMagicLink}>
              <span className="auth-kicker">Passwordless access</span>
              <h3>Save across devices</h3>
              <p>Kami akan mengirim magic link. Tanpa login, history tetap tersimpan secara lokal.</p>
              <label htmlFor="auth-email">Email</label>
              <div className="auth-email-row">
                <Mail size={15} />
                <input
                  id="auth-email"
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="you@example.com"
                  required
                />
              </div>
              <button className="auth-submit" type="submit" disabled={loading}>
                {loading ? "Sending..." : "Send magic link"}
              </button>
              {status && <p className="auth-feedback">{status}</p>}
            </form>
          )}
        </div>
      )}
    </div>
  );
}
