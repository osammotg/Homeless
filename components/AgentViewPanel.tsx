"use client";

import { useEffect, useRef } from "react";
import { ContactStatus } from "@/lib/types";

export default function AgentViewPanel({
  listingTitle,
  status,
  agentViewUrl,
  onSimulateReply,
  onClose,
}: {
  listingTitle: string;
  status: ContactStatus | null;
  agentViewUrl?: string | null;
  onSimulateReply: () => void;
  onClose: () => void;
}) {
  const endRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [status?.events?.length]);

  const settled = ["completed", "failed", "timed_out", "interrupted", "cancelled"];
  const live = status && !settled.includes(status.status);

  return (
    <div className="agentview">
      <header>
        <div className="t">
          {live && <span className="pulse" />}
          Agent View — contacting owner
        </div>
        <button className="ghost" onClick={onClose} style={{ padding: "2px 8px" }}>
          ✕
        </button>
      </header>
      <div className="events">
        <div className="muted">WhatsApp inquiry · {listingTitle}</div>
        {(status?.events ?? []).map((e, i) => (
          <div className="event" key={i}>
            <span className="step">{String(e.step).padStart(2, "0")}</span>
            {e.text}
          </div>
        ))}
        {!status?.events?.length && <div className="muted">Starting session…</div>}
        <div ref={endRef} />
      </div>
      <footer>
        <span className="badge">{status?.status ?? "pending"}</span>
        {agentViewUrl && (
          <a href={agentViewUrl} target="_blank" rel="noreferrer">
            Open in H Agent View ↗
          </a>
        )}
        <div style={{ flex: 1 }} />
        <button className="ghost" onClick={onSimulateReply} title="Owner replies (demo)">
          Owner replied
        </button>
      </footer>
    </div>
  );
}
