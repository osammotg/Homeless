"use client";

import { useEffect, useRef } from "react";
import { SessionEvent } from "@/lib/types";

const TERMINAL = ["completed", "failed", "timed_out", "interrupted", "cancelled"];

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
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events.length]);

  const live = !TERMINAL.includes(statusLabel);

  return (
    <div className="agentview">
      <header>
        <div className="t">
          {live && <span className="pulse" />}
          {title}
        </div>
        <button className="ghost" onClick={onClose} style={{ padding: "2px 8px" }}>
          ✕
        </button>
      </header>
      <div className="events">
        {subtitle && <div className="muted">{subtitle}</div>}
        {events.map((e, i) => (
          <div className="event" key={i}>
            <span className="step">{String(e.step).padStart(2, "0")}</span>
            {e.text}
          </div>
        ))}
        {!events.length && <div className="muted">Starting session…</div>}
        <div ref={endRef} />
      </div>
      <footer>
        <span className="badge">{statusLabel}</span>
        {agentViewUrl && (
          <a href={agentViewUrl} target="_blank" rel="noreferrer">
            Watch live in H Agent View ↗
          </a>
        )}
        <div style={{ flex: 1 }} />
        {action && (
          <button className="ghost" onClick={action.onClick}>
            {action.label}
          </button>
        )}
      </footer>
    </div>
  );
}
