import React from "react";
import { Card, CardContent } from "@/components/ui/card";

type CrawlResults = {
  reddit?: { title: string }[];
  github?: { name: string }[];
  hn?: { title: string }[];
};

interface CrawlResultsPanelProps {
  crawlResults: CrawlResults;
  crawlingStatus: string;
  isLoading: boolean;
  activeDomain: string | null;
  previewTemplate: string;
  templateError?: string | null;
  onFetchPreview: (domain: string) => void;
  onDownload: (domain: string) => void;
}

export function CrawlResultsPanel({
  crawlResults,
  crawlingStatus,
  isLoading,
  activeDomain,
  previewTemplate,
  templateError,
  onFetchPreview,
  onDownload,
}: CrawlResultsPanelProps) {
  if (Object.keys(crawlResults).length === 0) return null;

  return (
    <div className="mx-auto max-w-7xl px-4 py-4">
      <Card className="rounded-2xl border-slate-200">
        <CardContent className="p-4">
          {crawlingStatus && (
            <div className="mb-2 text-xs font-bold text-blue-600">상태: {crawlingStatus}</div>
          )}
          <div className="grid gap-4 md:grid-cols-3">
            {crawlResults.reddit && (
              <div>
                <div className="mb-2 text-xs font-medium text-slate-500">Reddit</div>
                <div className="space-y-1">
                  {crawlResults.reddit.map((r, i) => (
                    <div key={i} className="truncate text-sm">
                      {r.title}
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="mt-6 border-t pt-4">
              <div className="mb-2 text-sm font-bold text-slate-700">실전 운용 템플릿 생성</div>
              <div className="flex gap-2">
                <button
                  onClick={() => onFetchPreview("Unity")}
                  disabled={isLoading}
                  className={`rounded px-3 py-1 text-xs text-white ${
                    isLoading && activeDomain === "Unity" ? "bg-blue-400" : "bg-blue-600 hover:bg-blue-700"
                  }`}
                >
                  {isLoading && activeDomain === "Unity" ? "생성 중..." : "Unity 보기"}
                </button>
                <button
                  onClick={() => onFetchPreview("Backend")}
                  disabled={isLoading}
                  className={`rounded px-3 py-1 text-xs text-white ${
                    isLoading && activeDomain === "Backend" ? "bg-green-400" : "bg-green-600 hover:bg-green-700"
                  }`}
                >
                  {isLoading && activeDomain === "Backend" ? "생성 중..." : "Backend 보기"}
                </button>
              </div>

              {templateError && (
                <div className="mt-3 rounded border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
                  템플릿 미리보기 실패: {templateError}
                </div>
              )}

              {previewTemplate && (
                <div className="mt-4 animate-in fade-in rounded border border-slate-200 bg-white p-4 shadow-sm">
                  <h4 className="mb-2 text-sm font-semibold text-slate-800">{activeDomain} 운영 템플릿</h4>
                  <pre className="max-h-80 overflow-y-auto rounded bg-slate-100 p-3 text-xs whitespace-pre-wrap">
                    {previewTemplate}
                  </pre>
                  <button
                    onClick={() => onDownload(activeDomain || "default")}
                    className="mt-3 flex w-full justify-center rounded bg-red-600 py-2 text-sm font-medium text-white hover:bg-red-700"
                  >
                    📂 Zip으로 다운로드
                  </button>
                </div>
              )}
            </div>

            {crawlResults.github && (
              <div>
                <div className="mb-2 text-xs font-medium text-slate-500">GitHub</div>
                <div className="space-y-1">
                  {crawlResults.github.map((r, i) => (
                    <div key={i} className="truncate text-sm">
                      {r.name}
                    </div>
                  ))}
                </div>
              </div>
            )}
            {crawlResults.hn && (
              <div>
                <div className="mb-2 text-xs font-medium text-slate-500">Hacker News</div>
                <div className="space-y-1">
                  {crawlResults.hn.map((r, i) => (
                    <div key={i} className="truncate text-sm">
                      {r.title}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
