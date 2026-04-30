"use client";

import React, { useMemo, useState } from "react";
import Link from "next/link";

import type { Domain, RecommendedSetting } from "@/types";
import {
  downloadTemplateApi,
  fetchRecommendedSettingsApi,
  getCloneInstructionsApi,
  sendRecommendationFeedbackApi,
} from "@/lib/api";
import { domains } from "@/lib/constants";
import { RecommendedSettingCard } from "@/components/recommended/RecommendedSettingCard";
import { Button } from "@/components/ui/button";

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export default function RecommendationsPage() {
  const [settings, setSettings] = React.useState<RecommendedSetting[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [activeDomain, setActiveDomain] = useState<Domain>(domains[0]);
  const [status, setStatus] = useState("");
  const [note, setNote] = useState("");

  React.useEffect(() => {
    let mounted = true;
    const load = async () => {
      setLoading(true);
      try {
        const data = await fetchRecommendedSettingsApi();
        if (mounted) {
          setSettings(data);
        }
      } catch (e) {
        if (mounted) setStatus(`로드 실패: ${String(e)}`);
      } finally {
        if (mounted) setLoading(false);
      }
    };
    load();
    return () => {
      mounted = false;
    };
  }, []);

  const active = useMemo(
    () => settings.find((s) => s.domain === activeDomain) ?? settings[0],
    [settings, activeDomain],
  );

  const handleDownloadZip = async () => {
    if (!active) return;
    setStatus("템플릿 ZIP 생성 중...");
    try {
      const blob = await downloadTemplateApi(active.domain);
      downloadBlob(blob, `${active.domain}-ops-template.zip`);
      setStatus("ZIP 다운로드 완료");
    } catch (e) {
      setStatus(`ZIP 생성 실패: ${String(e)}`);
    }
  };

  const handleCloneScript = async () => {
    if (!active) return;
    setStatus("클론 스크립트 생성 중...");
    try {
      const data = await getCloneInstructionsApi(active.domain);
      await navigator.clipboard.writeText(data.script);
      setStatus("clone.sh 스크립트를 클립보드에 복사했습니다.");
    } catch (e) {
      setStatus(`클론 스크립트 생성 실패: ${String(e)}`);
    }
  };

  const handleFeedback = async (rating: number) => {
    if (!active) return;
    setStatus("피드백 저장 중...");
    try {
      await sendRecommendationFeedbackApi({
        domain: active.domain,
        rating,
        note,
        chosen_models: active.modelRouting,
        chosen_workflow: active.workflow,
      });
      setStatus("피드백 저장 완료 (지속 학습 반영)");
      const refreshed = await fetchRecommendedSettingsApi();
      setSettings(refreshed);
      setNote("");
    } catch (e) {
      setStatus(`피드백 저장 실패: ${String(e)}`);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-950">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4">
          <div>
            <h1 className="text-2xl font-bold">하네스 운영 추천 셋팅</h1>
            <p className="text-sm text-slate-600">도메인/카테고리 데이터 기반 하네스 운영 추천</p>
          </div>
          <div className="flex items-center gap-2">
            <Link href="/settings">
              <Button variant="outline">프로젝트 설정 보기</Button>
            </Link>
            <Link href="/">
              <Button variant="outline">보드로 돌아가기</Button>
            </Link>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-4 px-4 py-6">
        {loading ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-slate-500">
            추천 셋팅 데이터를 불러오는 중...
          </div>
        ) : (
          <>
            <RecommendedSettingCard
              settings={settings}
              activeSetting={activeDomain}
              onSelectSetting={setActiveDomain}
            />

            <div className="rounded-2xl border border-slate-200 bg-white p-4">
              <div className="mb-3 text-sm font-semibold text-slate-700">운영 액션</div>
              <div className="flex flex-wrap gap-2">
                <Button onClick={handleDownloadZip}>템플릿 ZIP 다운로드</Button>
                <Button variant="outline" onClick={handleCloneScript}>클론 스크립트 복사</Button>
                <Button variant="outline" onClick={() => handleFeedback(5)}>추천 좋음(5점)</Button>
                <Button variant="outline" onClick={() => handleFeedback(3)}>보통(3점)</Button>
                <Button variant="outline" onClick={() => handleFeedback(1)}>개선 필요(1점)</Button>
              </div>
              <textarea
                className="mt-3 w-full rounded-xl border border-slate-200 p-3 text-sm"
                rows={3}
                placeholder="추천 품질 개선에 도움이 되는 코멘트를 남겨주세요."
                value={note}
                onChange={(e) => setNote(e.target.value)}
              />
              {active && (
                <div className="mt-2 text-xs text-slate-500">
                  근거 데이터: {active.evidenceCount ?? 0}건 / 피드백: {active.feedbackCount ?? 0}건
                </div>
              )}
              {status && <div className="mt-2 text-sm text-blue-700">{status}</div>}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
