import React from "react";
import { cn } from "@/lib/utils";

interface InfoBlockProps {
  title: string;
  icon: React.ReactNode;
  items: string[];
  dark?: boolean;
}

export function InfoBlock({ title, icon, items, dark }: InfoBlockProps) {
  return (
    <div className={cn("rounded-2xl p-4", dark ? "bg-white/10 ring-1 ring-white/15" : "bg-slate-50")}>
      <div className={cn("flex items-center gap-2 text-sm font-bold", dark ? "text-blue-100" : "text-slate-800")}>
        {icon} {title}
      </div>
      <ul className={cn("mt-2 space-y-1.5 text-sm", dark ? "text-slate-200" : "text-slate-600")}>
        {items.map((item) => (
          <li key={item} className="flex gap-2">
            <span className={cn("mt-2 h-1.5 w-1.5 shrink-0 rounded-full", dark ? "bg-blue-300" : "bg-blue-500")} />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
