import React from "react";
import type { Domain } from "@/types";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Settings2 } from "lucide-react";

interface TemplateServiceProps {
  agentsTemplate: string;
  activeDomain: Domain;
  template: string;
  generating: boolean;
  onGenerate: (domain: string) => void;
}

export function TemplateService({
  agentsTemplate,
  activeDomain,
  template,
  generating,
  onGenerate,
}: TemplateServiceProps) {
  return (
    <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
      <CardContent className="p-5">
        <h2 className="flex items-center gap-2 text-lg font-bold">
          <Settings2 className="h-5 w-5" /> 실전 운용 템플릿
        </h2>
        <p className="mt-1 text-sm leading-6 text-slate-600">
          Rule + Skill + AGENTS.md를 한 카테고리로 합친 운영 템플릿.
        </p>
        <pre className="mt-4 max-h-[360px] overflow-auto rounded-2xl bg-slate-950 p-4 text-xs leading-5 text-slate-100">
          {agentsTemplate}
        </pre>
        <Button
          className="mt-4 w-full rounded-2xl"
          onClick={() => onGenerate(activeDomain)}
          disabled={generating}
        >
          {generating ? "생성 중..." : "AI 템플릿 생성"}
        </Button>
        {template && (
          <pre className="mt-4 max-h-[360px] overflow-auto rounded-2xl bg-slate-950 p-4 text-xs leading-5 text-slate-100">
            {template}
          </pre>
        )}
      </CardContent>
    </Card>
  );
}
