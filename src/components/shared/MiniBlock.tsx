import React from "react";

interface MiniBlockProps {
  title: string;
  value: string;
}

export function MiniBlock({ title, value }: MiniBlockProps) {
  return (
    <div className="rounded-2xl border border-slate-100 bg-slate-50 p-3">
      <div className="text-xs font-bold uppercase tracking-wide text-slate-500">{title}</div>
      <div className="mt-1 text-sm text-slate-800">{value}</div>
    </div>
  );
}
