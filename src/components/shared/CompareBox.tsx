import React from "react";
import { cn } from "@/lib/utils";

interface CompareBoxProps {
  type: "bad" | "good";
  title: string;
  text: string;
}

export function CompareBox({ type, title, text }: CompareBoxProps) {
  return (
    <div
      className={cn(
        "rounded-2xl border p-3",
        type === "bad" ? "border-red-100 bg-red-50" : "border-emerald-100 bg-emerald-50"
      )}
    >
      <div className={cn("text-xs font-bold", type === "bad" ? "text-red-700" : "text-emerald-700")}>{title}</div>
      <div className="mt-1 text-sm text-slate-700">{text}</div>
    </div>
  );
}
