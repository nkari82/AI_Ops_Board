import React from "react";
import { cn } from "@/lib/utils";

interface PillProps {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}

export function Pill({ active, onClick, children }: PillProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "rounded-full px-3 py-1.5 text-sm transition",
        active ? "bg-slate-950 text-white shadow-sm" : "bg-slate-100 text-slate-700 hover:bg-slate-200"
      )}
    >
      {children}
    </button>
  );
}
