"use client";
import React, { useMemo, useState, useCallback } from "react";
import Link from "next/link";
import type { BoardCategory, Domain } from "@/types";
import { useBoardData } from "@/hooks/useBoardData";
import { useCrawler } from "@/hooks/useCrawler";
import { useTemplateService } from "@/hooks/useTemplateService";
import { Metric } from "@/components/shared/Metric";
import { BoardFilters } from "@/components/board/BoardFilters";
import { OperationPostCard } from "@/components/board/OperationPostCard";
import { CrawlResultsPanel } from "@/components/crawler/CrawlResultsPanel";
import { Button } from "@/components/ui/button";
import {
  Globe2,
  Layers3,
  RefreshCw,
  ShieldAlert,
  Sparkles,
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8005";

export default function AiOpsBoard() {
  const [query, setQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<BoardCategory | "전체">("전체");
  const [selectedDomain, setSelectedDomain] = useState<Domain | "전체">("전체");
  const [llmTestStatus, setLlmTestStatus] = useState<string>("");

  const testLlmConnection = async () => {
    setLlmTestStatus("테스트 중...");
    try {
      const response = await fetch(`${API_BASE}/api/test-llm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: "Hello, are you working?" })
      });
      const data = await response.json();
      setLlmTestStatus(data.status === "success" ? "성공!" : "실패");
      console.log("LLM Response:", data.response);
    } catch (e) {
      setLlmTestStatus("에러 발생");
      console.error("LLM Test failed:", e);
    }
  };

  // const { userPosts, fetchKnowledge, registerUserPost } = useBoardData();
  // const { fetchKnowledge } = useBoardData(); // 이 부분은 아래와 같이 수정됨
  const { fetchKnowledge, visiblePosts, allPosts, loadMore, hasMore } = useBoardData();
  const { crawlResults, crawling, crawlingStatus, testCrawl } = useCrawler(fetchKnowledge);
  const {
    isLoading,
    activeDomain,
    previewTemplate,
    fetchTemplatePreview,
    downloadTemplate,
  } = useTemplateService();
  const [latestNews, setLatestNews] = useState<Array<{ title: string; url: string; source: string }>>([]);

  // 데이터 로딩 부분은 useBoardData로 이동하여 제거함
  // fetchPostsData 제거
  
  React.useEffect(() => {
    const news = allPosts.slice(0, 3).map((p) => ({
      title: p.title,
      url: p.sources[0] || "#",
      source: p.sourceKind,
    }));
    setLatestNews(news);
  }, [allPosts]);

  React.useEffect(() => {
    fetchKnowledge();
  }, [fetchKnowledge]);

  // ... (existing logic)

  const filteredPosts = useMemo(() => {
    const q = query.trim().toLowerCase();
    
    return allPosts.filter((post) => {
      if (!post) return false;
      
      const categoryOk = selectedCategory === "전체" || post.category === selectedCategory;
      const domainOk = selectedDomain === "전체" || post.domain === selectedDomain;
      
      const queryOk =
        q.length === 0 ||
        [post.title, post.summary, post.domain, post.category, ...(post.tags || [])]
          .filter(Boolean)
          .join(" ")
          .toLowerCase()
          .includes(q);
      return categoryOk && domainOk && queryOk;
    });
  }, [query, selectedCategory, selectedDomain, allPosts]);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-950">
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/90 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-4 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="flex items-center gap-2 text-sm font-semibold text-blue-600">
              <Sparkles className="h-4 w-4" /> AI 운용 지식을 자동 수집·요약·축적·합성하는 보드
            </div>
            <h1 className="mt-1 text-2xl font-bold tracking-tight md:text-3xl">AI Ops Board</h1>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-sm text-slate-600">
            <Button
              size="sm"
              variant={crawling ? "secondary" : "default"}
              onClick={testCrawl}
              disabled={crawling}
            >
              <RefreshCw className={`h-3.5 w-3.5 mr-1 ${crawling ? "animate-spin" : ""}`} />
              {crawling ? "크롤링 중..." : "최신 뉴스 업데이트"}
            </Button>
            <Link href="/recommendations">
              <Button size="sm" variant="outline">추천 셋팅 보기</Button>
            </Link>
            <Button size="sm" variant="outline" onClick={testLlmConnection}>
              <Sparkles className="h-3.5 w-3.5 mr-1" />
              LLM 연결 테스트
            </Button>
            {llmTestStatus && <span className="text-sm font-bold">{llmTestStatus}</span>}
          </div>
        </div>
      </header>

      <CrawlResultsPanel
        crawlResults={crawlResults}
        crawlingStatus={crawlingStatus}
        isLoading={isLoading}
        activeDomain={activeDomain}
        previewTemplate={previewTemplate}
        onFetchPreview={fetchTemplatePreview}
        onDownload={downloadTemplate}
      />

      <main className="mx-auto max-w-7xl space-y-6 px-4 py-6">
        {/* [REMOVED: RecommendedSettingCard & LlmRouter] */}

        <section className="grid gap-4 md:grid-cols-3">
          <Metric icon={<Globe2 className="h-5 w-5" />} label="자동 수집 보드" value="크롤링 + AI" caption="실시간 연동" />
          <Metric icon={<Layers3 className="h-5 w-5" />} label="실전 운용" value="Rule+Skill" caption="AGENTS.md 포함" />
          <Metric icon={<ShieldAlert className="h-5 w-5" />} label="MCP" value="권한 분리" caption="위험도 라벨링" />
        </section>

        <BoardFilters
          query={query}
          selectedCategory={selectedCategory}
          selectedDomain={selectedDomain}
          onQueryChange={setQuery}
          onCategoryChange={setSelectedCategory}
          onDomainChange={setSelectedDomain}
        />

        <section className="space-y-4">
          {filteredPosts.length > 0 ? (
            <>
              {filteredPosts.slice(0, visiblePosts.length).map((post) => (
                <OperationPostCard key={post.id} post={post} />
              ))}
              {hasMore && (
                <div className="text-center">
                  <Button onClick={loadMore} variant="outline">더 보기</Button>
                </div>
              )}
            </>
          ) : (
            <div className="rounded-3xl border border-slate-200 bg-white p-8 text-center text-slate-500">
              표시할 운용 포스트가 없습니다. 크롤링을 실행하거나 필터를 조정하세요.
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
