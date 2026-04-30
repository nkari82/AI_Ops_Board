import React from "react";
import type { Domain, RecommendedSetting } from "@/types";
import { Card, CardContent } from "@/components/ui/card";
import { InfoBlock } from "@/components/shared/InfoBlock";
import { Bot, Flame, GitBranch, Network, Wrench } from "lucide-react";
import { motion } from "framer-motion";

interface RecommendedSettingCardProps {
  settings: RecommendedSetting[];
  activeSetting: Domain;
}

export function RecommendedSettingCard({
  settings,
  activeSetting,
}: RecommendedSettingCardProps) {
  const setting = settings.find((item) => item.domain === activeSetting) ?? settings[0];

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
      <Card className="overflow-hidden rounded-3xl border-blue-100 bg-gradient-to-br from-blue-950 via-slate-900 to-slate-950 text-white shadow-xl">
        <CardContent className="p-6 md:p-8">
          <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
            <div className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-sm text-blue-100 ring-1 ring-white/15">
              <Flame className="h-4 w-4" /> 추천 셋팅
            </div>
            {setting && (
              <span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-sm font-bold text-emerald-700">
                {setting.score ?? 0}
              </span>
            )}
          </div>

          {setting && (
            <div className="mt-7 grid gap-6 md:grid-cols-[0.9fr_1.1fr]">
              <div>
                <h2 className="text-2xl font-bold leading-tight md:text-3xl">{setting.title}</h2>
                <p className="mt-3 text-sm leading-6 text-slate-300">{setting.reason}</p>

                {setting.qualityBand && (
                  <div className="mt-3 inline-flex items-center rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-xs font-semibold text-sky-700">
                    추천 신뢰도: {setting.qualityBand.toUpperCase()} ({Math.round((setting.qualityConfidence ?? 0) * 100)}%)
                  </div>
                )}

                {setting.scoreBreakdown && (
                  <div className="mt-4 rounded-xl border border-white/20 bg-white/5 p-3 text-xs text-slate-200">
                    <div className="mb-2 font-semibold text-slate-100">점수 구성요소</div>
                    <ul className="space-y-1">
                      <li>baseScore: {setting.scoreBreakdown.baseScore}</li>
                      <li>feedbackBonus: {setting.scoreBreakdown.feedbackBonus}</li>
                      <li>comboBoost: {setting.scoreBreakdown.comboBoost}</li>
                      <li>sparsePenaltyApplied: {setting.scoreBreakdown.sparsePenaltyApplied ? "yes" : "no"}</li>
                      <li>finalScore: {setting.scoreBreakdown.finalScore}</li>
                    </ul>
                  </div>
                )}

                {setting.evidenceHighlights?.length ? (
                  <div className="mt-4 rounded-xl border border-white/20 bg-white/5 p-3 text-xs text-slate-200">
                    <div className="mb-2 font-semibold text-slate-100">주요 근거 Top 3</div>
                    <ul className="list-disc space-y-1 pl-4">
                      {setting.evidenceHighlights.slice(0, 3).map((line) => (
                        <li key={line}>{line}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </div>
              <div className="grid gap-3">
                <InfoBlock title="Model Routing" icon={<Bot className="h-4 w-4" />} items={setting.modelRouting} dark />
                <InfoBlock title="Workflow" icon={<GitBranch className="h-4 w-4" />} items={setting.workflow} dark />
                <InfoBlock title="MCP / Plugins" icon={<Network className="h-4 w-4" />} items={setting.mcp} dark />
                <InfoBlock title="Rules" icon={<Wrench className="h-4 w-4" />} items={setting.rules} dark />
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}
