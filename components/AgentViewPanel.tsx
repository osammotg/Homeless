"use client";

import { useEffect, useRef, useState } from "react";
import { SessionEvent } from "@/lib/types";

const TERMINAL = ["completed", "failed", "timed_out", "interrupted", "cancelled", "booked", "done"];

function classify(text: string): { cls: string; who: string; body: string } {
  if (/^owner:/i.test(text)) return { cls: "owner", who: "owner", body: text.replace(/^owner:\s*/i, "") };
  if (/^agent:/i.test(text)) return { cls: "agent", who: "agent", body: text.replace(/^agent:\s*/i, "") };
  return { cls: "", who: "", body: text };
}

export default function AgentViewPanel({
  title,
  subtitle,
  statusLabel,
  events,
  agentViewUrl,
  onClose,
  action,
}: {
  title: string;
  subtitle?: string;
  statusLabel: string;
  events: SessionEvent[];
  agentViewUrl?: string | null;
  onClose: () => void;
  action?: { label: string; onClick: () => void };
}) {
  const endRef = useRef<HTMLDivElement>(null);
  const [elapsed, setElapsed] = useState(0);
  const live = !TERMINAL.includes(statusLabel);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events.length]);

  useEffect(() => {
    if (!live) return;
    const t = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(t);
  }, [live]);

  const mmss = `${String(Math.floor(elapsed / 60)).padStart(2, "0")}:${String(elapsed % 60).padStart(2, "0")}`;
  const sid = agentViewUrl?.split("/").pop()?.slice(0, 8);

  return (
    <div className="agentview">
      <header>
        <span className="label">
          {live && <span className="pulse" />}
          {live ? "live · agent" : "agent · done"}
        </span>
        <span className="timer">{mmss}</span>
        {sid && <span className="sid">{sid}</span>}
      </header>
      <div className="title">{title}</div>
      {subtitle && <div className="sub">{subtitle}</div>}
      <div className="events">
        {events.map((e, i) => {
          const c = classify(e.text);
          return (
            <div className={`event ${c.cls}`} key={i}>
              <span className="step">{String(e.step).padStart(2, "0")}</span>
              {c.who && <span className="who">{c.who}</span>}
              {c.body}
            </div>
          );
        })}
        {!events.length && <div className="muted">connecting…</div>}
        <div ref={endRef} />
      </div>
      <footer>
        <span className="badge agent">{statusLabel}</span>
        {action && (
          <button className="ghost" onClick={action.onClick}>
            {action.label}
          </button>
        )}
        <button className="ghost" onClick={onClose}>Close</button>
        {agentViewUrl && (
          <a className="watch" href={agentViewUrl} target="_blank" rel="noreferrer">
            Watch live in H Agent View
          </a>
        )}
      </footer>
    </div>
  );
}
