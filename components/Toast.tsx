"use client";

export default function Toast({ message }: { message: string }) {
  return (
    <div className="toast">
      <span className="k">Found you a place</span>
      <span>{message}</span>
    </div>
  );
}
