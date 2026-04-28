import type { SourceKind } from "@/types";
import { cn } from "@/lib/utils";

export function riskClass(risk: "low" | "medium" | "high"): string {
  if (risk === "high") return "border-red-200 bg-red-50 text-red-700";
  if (risk === "medium") return "border-amber-200 bg-amber-50 text-amber-700";
  return "border-emerald-200 bg-emerald-50 text-emerald-700";
}

export function sourceLabel(kind: SourceKind): string {
  switch (kind) {
    case "manual_user_input":
      return "수동 입력";
    case "crawled":
      return "웹 크롤링";
    case "ai_summarized":
      return "AI 요약";
    case "accumulated":
      return "축적 데이터";
    case "ai_synthesized":
      return "AI 합성";
  }
}

export { cn };
