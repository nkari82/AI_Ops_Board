"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";

import type { Domain, RecommendedSetting } from "@/types";
import {
  crawlYoutubeSearchApi,
  downloadTemplateApi,
  fetchAdminMetricsApi,
  fetchCrawlTaskStatusApi,
  fetchHealthDetailedApi,
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

function formatKoreanDateTime(value?: string | null): string {
  if (!value) return "-";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "-";
  return d.toLocaleString("ko-KR", { hour12: false });
}

export default function RecommendationsPage() {
  const [settings, setSettings] = React.useState<RecommendedSetting[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [activeDomain, setActiveDomain] = useState<Domain>(domains[0]);
  const [status, setStatus] = useState("");
  const [note, setNote] = useState("");
  const [metrics, setMetrics] = useState<{
    quality?: { totalPosts?: number; pollutedPosts?: number; qualityScore?: number };
    errors?: { total?: number; byCategory?: Record<string, number> };
    rssQuality?: {
      entryBlocksTotal?: number;
      extractedLinksTotal?: number;
      acceptedLinksTotal?: number;
      skippedLinksTotal?: number;
      acceptanceRate?: number | null;
      skippedByReason?: Record<string, number>;
    };
    youtubeSearch?: {
      activeCount?: number;
      deduplicated?: number;
      rateLimited?: number;
      completed?: number;
      failed?: number;
      requested?: number;
      queued?: number;
      lastQuery?: string | null;
      lastTaskId?: string | null;
      lastStatus?: string | null;
      updatedAt?: string | null;
      recentTaskSummaries?: Array<{
        taskId?: string;
        status?: string;
        resultCount?: number | null;
        query?: string;
        updatedAt?: string;
        completedAt?: string;
      }>;
    };
  } | null>(null);
  const [health, setHealth] = useState<{
    status: string;
    timestamp?: string;
    sloBreached?: boolean;
    checks?: Record<string, unknown>;
  } | null>(null);
  const [ytQuery, setYtQuery] = useState("AI coding agent");
  const [ytMaxResults, setYtMaxResults] = useState(6);
  const [ytPages, setYtPages] = useState(2);
  const [ytTaskId, setYtTaskId] = useState<string | null>(null);
  const [ytTaskStatus, setYtTaskStatus] = useState<string | null>(null);
  const [ytPolling, setYtPolling] = useState(false);
  const [ytStatusMessage, setYtStatusMessage] = useState("");
  const [ytPollingErrorCount, setYtPollingErrorCount] = useState(0);
  const [ytPollingIntervalMs, setYtPollingIntervalMs] = useState(3000);
  const pollingTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pollingIntervalMsRef = useRef(3000);
  const pollingErrorCountRef = useRef(0);

  const refreshOpsSnapshot = React.useCallback(async () => {
    const [metricsData, healthData] = await Promise.all([
      fetchAdminMetricsApi(),
      fetchHealthDetailedApi(),
    ]);
    setMetrics(metricsData);
    setHealth(healthData);
  }, []);

  React.useEffect(() => {
    let mounted = true;
    const load = async () => {
      setLoading(true);
      try {
        const [data, metricsData, healthData] = await Promise.all([
          fetchRecommendedSettingsApi(),
          fetchAdminMetricsApi(),
          fetchHealthDetailedApi(),
        ]);
        if (mounted) {
          setSettings(data);
          setMetrics(metricsData);
          setHealth(healthData);
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
    [settings, activeDomain]
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

  const handleYoutubeSearchStart = async () => {
    const query = ytQuery.trim();
    if (!query) {
      setYtStatusMessage("검색어를 입력해 주세요.");
      return;
    }

    setYtStatusMessage("YouTube 검색 크롤 요청 중...");
    try {
      const response = await crawlYoutubeSearchApi({
        query,
        max_results: ytMaxResults,
        pages: ytPages,
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data?.detail || "YouTube 검색 크롤 요청 실패");
      }

      const taskId = String(data.task_id || "");
      setYtTaskId(taskId || null);
      setYtTaskStatus(data.status || "PENDING");
      setYtPolling(Boolean(taskId));
      setYtPollingErrorCount(0);
      pollingErrorCountRef.current = 0;
      setYtPollingIntervalMs(3000);
      pollingIntervalMsRef.current = 3000;
      setYtStatusMessage(
        data.deduplicated
          ? `중복 요청 감지: 기존 작업 재사용 (${taskId})`
          : `작업 시작됨 (${taskId})`
      );

      await refreshOpsSnapshot();
    } catch (e) {
      setYtStatusMessage(`요청 실패: ${String(e)}`);
    }
  };

  useEffect(() => {
    if (!ytPolling || !ytTaskId) return;

    let cancelled = false;

    const poll = async () => {
      try {
        const data = await fetchCrawlTaskStatusApi(ytTaskId);
        if (cancelled) return;

        const status = String(data.status || "UNKNOWN");
        setYtTaskStatus(status);
        setYtPollingErrorCount(0);
        pollingErrorCountRef.current = 0;
        setYtPollingIntervalMs(3000);
        pollingIntervalMsRef.current = 3000;

        if (["SUCCESS", "FAILURE", "REVOKED"].includes(status)) {
          setYtPolling(false);
          if (status === "SUCCESS") {
            const resultCount = Array.isArray(data.result) ? data.result.length : null;
            setYtStatusMessage(
              resultCount !== null
                ? `완료: ${resultCount}개 영상 처리`
                : "완료: 작업이 성공적으로 끝났습니다"
            );
          } else {
            setYtStatusMessage(`작업 종료 상태: ${status}`);
          }
          await refreshOpsSnapshot();
          return;
        }
      } catch (e) {
        if (cancelled) return;

        const next = pollingErrorCountRef.current + 1;
        pollingErrorCountRef.current = next;
        setYtPollingErrorCount(next);

        const backoff = Math.min(15000, 3000 * 2 ** Math.min(next, 3));
        pollingIntervalMsRef.current = backoff;
        setYtPollingIntervalMs(backoff);

        if (next >= 3) {
          setYtPolling(false);
          setYtStatusMessage(`상태 조회 실패(연속 ${next}회): 자동 폴링을 중지했습니다. 재시도를 눌러주세요.`);
        } else {
          setYtStatusMessage(`상태 조회 실패(${next}회): ${String(e)} / ${Math.round(backoff / 1000)}초 후 재시도`);
        }
      }

      if (!cancelled && ytPolling) {
        pollingTimeoutRef.current = setTimeout(poll, pollingIntervalMsRef.current);
      }
    };

    pollingTimeoutRef.current = setTimeout(poll, 0);

    return () => {
      cancelled = true;
      if (pollingTimeoutRef.current) {
        clearTimeout(pollingTimeoutRef.current);
        pollingTimeoutRef.current = null;
      }
    };
  }, [ytPolling, ytTaskId, refreshOpsSnapshot]);

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
            <h1 className="text-2xl font-bold">추천 셋팅</h1>
            <p className="text-sm text-slate-600">도메인/카테고리 데이터 기반 운용 추천</p>
          </div>
          <Link href="/">
            <Button variant="outline">보드로 돌아가기</Button>
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-4 px-4 py-6">
        <section className="grid gap-3 md:grid-cols-5">
          <div className="rounded-2xl border border-slate-200 bg-white p-4">
            <div className="text-xs text-slate-500">서비스 상태</div>
            <div className="mt-1 text-lg font-bold text-slate-900">{health?.status ?? "unknown"}</div>
            <div className="mt-1 text-[11px] text-slate-500">last check: {formatKoreanDateTime(health?.timestamp)}</div>
            {health?.sloBreached ? (
              <div className="mt-2 inline-flex rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-700">
                SLO breached
              </div>
            ) : null}
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-4">
            <div className="text-xs text-slate-500">수집 포스트</div>
            <div className="mt-1 text-lg font-bold text-slate-900">{metrics?.quality?.totalPosts ?? 0}</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-4">
            <div className="text-xs text-slate-500">오염 데이터</div>
            <div className="mt-1 text-lg font-bold text-slate-900">{metrics?.quality?.pollutedPosts ?? 0}</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-4">
            <div className="text-xs text-slate-500">품질 점수</div>
            <div className="mt-1 text-lg font-bold text-slate-900">{metrics?.quality?.qualityScore ?? 0}</div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-4">
            <div className="text-xs text-slate-500">누적 오류</div>
            <div className="mt-1 text-lg font-bold text-slate-900">{metrics?.errors?.total ?? 0}</div>
          </div>
        </section>
        <section className="grid gap-3 md:grid-cols-2">
          <div className="rounded-2xl border border-slate-200 bg-white p-4">
            <div className="mb-2 text-xs font-semibold text-slate-500">오류 카테고리 분포</div>
            {metrics?.errors?.byCategory && Object.keys(metrics.errors.byCategory).length > 0 ? (
              <ul className="space-y-1 text-sm text-slate-700">
                {Object.entries(metrics.errors.byCategory)
                  .sort((a, b) => b[1] - a[1])
                  .slice(0, 5)
                  .map(([name, count]) => (
                    <li key={name} className="flex items-center justify-between gap-3">
                      <span className="truncate">{name}</span>
                      <span className="font-semibold">{count}</span>
                    </li>
                  ))}
              </ul>
            ) : (
              <div className="text-sm text-slate-500">최근 오류가 없습니다.</div>
            )}
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-4">
            <div className="mb-2 text-xs font-semibold text-slate-500">헬스 체크 상세</div>
            <div className="space-y-1 text-sm text-slate-700">
              {health?.checks ? (
                Object.entries(health.checks).map(([key, value]) => {
                  const status =
                    typeof value === "object" && value && "status" in (value as Record<string, unknown>)
                      ? String((value as Record<string, unknown>).status)
                      : "ok";
                  return (
                    <div key={key} className="flex items-center justify-between gap-3">
                      <span className="capitalize">{key}</span>
                      <span className="font-semibold">{status}</span>
                    </div>
                  );
                })
              ) : (
                <div className="text-slate-500">체크 데이터가 없습니다.</div>
              )}
            </div>
          </div>
        </section>

        <section className="grid gap-3 md:grid-cols-2">
          <div className="rounded-2xl border border-slate-200 bg-white p-4">
            <div className="mb-2 text-xs font-semibold text-slate-500">RSS 품질 요약</div>
            <div className="grid grid-cols-2 gap-2 text-xs text-slate-700">
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-2">entryBlocks: <span className="font-semibold">{metrics?.rssQuality?.entryBlocksTotal ?? 0}</span></div>
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-2">extractedLinks: <span className="font-semibold">{metrics?.rssQuality?.extractedLinksTotal ?? 0}</span></div>
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-2">acceptedLinks: <span className="font-semibold">{metrics?.rssQuality?.acceptedLinksTotal ?? 0}</span></div>
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-2">skippedLinks: <span className="font-semibold">{metrics?.rssQuality?.skippedLinksTotal ?? 0}</span></div>
            </div>
            <div className="mt-2 text-xs text-slate-600">
              acceptanceRate: <span className="font-semibold">{(((metrics?.rssQuality?.acceptanceRate ?? 0) * 100).toFixed(1))}%</span>
            </div>
            <div className="mt-2 text-xs font-semibold text-slate-700">Skip reason Top 5</div>
            {metrics?.rssQuality?.skippedByReason && Object.keys(metrics.rssQuality.skippedByReason).length > 0 ? (
              <ul className="mt-1 space-y-1 text-xs text-slate-700">
                {Object.entries(metrics.rssQuality.skippedByReason)
                  .sort((a, b) => b[1] - a[1])
                  .slice(0, 5)
                  .map(([reason, count]) => (
                    <li key={reason} className="flex items-center justify-between gap-2 rounded border border-slate-200 bg-slate-50 px-2 py-1">
                      <span className="truncate">{reason}</span>
                      <span className="font-semibold">{count}</span>
                    </li>
                  ))}
              </ul>
            ) : (
              <div className="mt-1 text-xs text-slate-500">최근 스킵 사유 데이터가 없습니다.</div>
            )}
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-4">
            <div className="mb-3 text-sm font-semibold text-slate-700">YouTube 자동 검색 크롤</div>
          <div className="grid gap-2 md:grid-cols-4">
            <input
              className="rounded-xl border border-slate-200 px-3 py-2 text-sm"
              placeholder="검색어"
              value={ytQuery}
              onChange={(e) => setYtQuery(e.target.value)}
            />
            <input
              className="rounded-xl border border-slate-200 px-3 py-2 text-sm"
              type="number"
              min={1}
              max={30}
              value={ytMaxResults}
              onChange={(e) => setYtMaxResults(Math.max(1, Number(e.target.value || 1)))}
            />
            <input
              className="rounded-xl border border-slate-200 px-3 py-2 text-sm"
              type="number"
              min={1}
              max={5}
              value={ytPages}
              onChange={(e) => setYtPages(Math.max(1, Number(e.target.value || 1)))}
            />
            <Button onClick={handleYoutubeSearchStart}>YouTube 검색 실행</Button>
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-600">
            <span>taskId: {ytTaskId ?? "-"}</span>
            <span>/ status: {ytTaskStatus ?? "-"}</span>
            <span>/ polling: {ytPolling ? "on" : "off"}</span>
            <span>/ interval: {Math.round(ytPollingIntervalMs / 1000)}s</span>
            <span>/ errors: {ytPollingErrorCount}</span>
            {!ytPolling && ytTaskId && ytTaskStatus && !["SUCCESS", "FAILURE", "REVOKED"].includes(ytTaskStatus) && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setYtPolling(true);
                  setYtPollingErrorCount(0);
                  pollingErrorCountRef.current = 0;
                  setYtPollingIntervalMs(3000);
                  pollingIntervalMsRef.current = 3000;
                  setYtStatusMessage("수동 재시도: 폴링을 재개합니다.");
                }}
              >
                폴링 재시도
              </Button>
            )}
          </div>
          {ytStatusMessage && <div className="mt-2 text-sm text-blue-700">{ytStatusMessage}</div>}
          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-500">
            <span>lastUpdated: {formatKoreanDateTime(metrics?.youtubeSearch?.updatedAt)}</span>
            <span>/ lastQuery: {metrics?.youtubeSearch?.lastQuery || "-"}</span>
            <span>/ lastStatus: {metrics?.youtubeSearch?.lastStatus || "-"}</span>
            <Button
              variant="outline"
              size="sm"
              onClick={async () => {
                try {
                  await refreshOpsSnapshot();
                  setYtStatusMessage("운영 스냅샷을 수동 갱신했습니다.");
                } catch (e) {
                  setYtStatusMessage(`운영 스냅샷 갱신 실패: ${String(e)}`);
                }
              }}
            >
              스냅샷 갱신
            </Button>
          </div>
          <div className="mt-2 rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700">
            <div className="font-semibold text-slate-800">YouTube Runtime Metrics</div>
            <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1">
              <span>requested: {metrics?.youtubeSearch?.requested ?? 0}</span>
              <span>queued: {metrics?.youtubeSearch?.queued ?? 0}</span>
              <span>active: {metrics?.youtubeSearch?.activeCount ?? 0}</span>
              <span>dedup: {metrics?.youtubeSearch?.deduplicated ?? 0}</span>
              <span>rateLimited: {metrics?.youtubeSearch?.rateLimited ?? 0}</span>
              <span>completed: {metrics?.youtubeSearch?.completed ?? 0}</span>
              <span>failed: {metrics?.youtubeSearch?.failed ?? 0}</span>
            </div>
            <div className="mt-2 font-semibold text-slate-800">최근 작업 요약</div>
            {metrics?.youtubeSearch?.recentTaskSummaries && metrics.youtubeSearch.recentTaskSummaries.length > 0 ? (
              <ul className="mt-1 space-y-1">
                {metrics.youtubeSearch.recentTaskSummaries.slice(0, 5).map((item, idx) => (
                  <li key={`${item.taskId ?? "unknown"}-${idx}`} className="rounded border border-slate-200 bg-white px-2 py-1">
                    <span className="font-medium">{item.status ?? "-"}</span>
                    <span className="ml-2">count: {item.resultCount ?? 0}</span>
                    <span className="ml-2">query: {item.query || "-"}</span>
                    <span className="ml-2 text-slate-500">{formatKoreanDateTime(item.updatedAt ?? item.completedAt)}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="mt-1 text-slate-500">아직 요약된 작업이 없습니다.</div>
            )}
          </div>
          </div>
        </section>

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
              <div className="mb-3 text-sm font-semibold text-slate-700">실행 액션</div>
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
