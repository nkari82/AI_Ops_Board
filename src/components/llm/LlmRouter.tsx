import React from "react";
import type { LlmModel } from "@/types";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { Bot } from "lucide-react";

interface LlmRouterProps {
  models: LlmModel[];
  selectedModel: string;
  onSelectModel: (id: string) => void;
}

export function LlmRouter({ models, selectedModel, onSelectModel }: LlmRouterProps) {
  const model = models.find((item) => item.id === selectedModel) ?? models[0];

  return (
    <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
      <CardContent className="p-5">
        <h2 className="flex items-center gap-2 text-lg font-bold">
          <Bot className="h-5 w-5 text-blue-600" /> LLM Router
        </h2>
        <p className="mt-1 text-sm leading-6 text-slate-600">
          무료/로컬 모델은 탐색·요약·분류, 유료 모델은 고급 판단·리뷰에만 사용한다.
        </p>
        <div className="mt-4 grid gap-2">
          {models.map((item) => (
            <button
              key={item.id}
              onClick={() => onSelectModel(item.id)}
              className={cn(
                "rounded-2xl border p-3 text-left transition",
                selectedModel === item.id
                  ? "border-slate-950 bg-slate-950 text-white"
                  : "border-slate-200 bg-slate-50 hover:bg-slate-100"
              )}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="font-semibold">{item.name}</div>
                <span
                  className={cn(
                    "rounded-full px-2 py-0.5 text-xs",
                    selectedModel === item.id ? "bg-white/15" : "bg-white text-slate-600"
                  )}
                >
                  {item.cost}
                </span>
              </div>
              <div
                className={cn(
                  "mt-1 text-xs",
                  selectedModel === item.id ? "text-slate-300" : "text-slate-500"
                )}
              >
                {item.role}
              </div>
            </button>
          ))}
        </div>
        <div className="mt-4 rounded-2xl border border-slate-100 bg-slate-50 p-3">
          <div className="text-xs font-bold uppercase tracking-wide text-slate-500">Selected endpoint</div>
          <code className="mt-1 block break-all text-xs text-slate-800">{model.endpoint}</code>
        </div>
      </CardContent>
    </Card>
  );
}
