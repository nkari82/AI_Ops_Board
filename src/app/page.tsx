"use client";
import React, { useMemo, useState } from "react";
import Link from "next/link";
import type { BoardCategory, Domain } from "@/types";
import { useBoardData } from "@/hooks/useBoardData";
import { useCrawler } from "@/hooks/useCrawler";
import { useTemplateService } from "@/hooks/useTemplateService";
import { testLlmApi } from "@/lib/api";
import { BoardFilters } from "@/components/board/BoardFilters";
import { OperationPostCard } from "@/components/board/OperationPostCard";
import { CrawlResultsPanel } from "@/components/crawler/CrawlResultsPanel";
import { Button } from "@/components/ui/button";
import {
  RefreshCw,
  Sparkles,
} from "lucide-react";

export default function AiOpsBoard() {
  const [query, setQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<BoardCategory | "전체">("전체");
  const [selectedDomain, setSelectedDomain] = useState<Domain | "전체">("전체");
  const [llmTestStatus, setLlmTestStatus] = useState<string>("");

  const testLlmConnection = async () => {
    setLlmTestStatus("테스트 중...");
    try {
      const data = await testLlmApi("Hello, are you working?");
      setLlmTestStatus(data.status === "success" ? "성공!" : "실패");
      console.log("LLM Response:", data.response);
    } catch (e) {
      setLlmTestStatus("에러 발생");
      console.error("LLM Test failed:", e);
    }
  };

  // const { userPosts, fetchKnowledge, registerUserPost } = useBoardData();
  // const { fetchKnowledge } = useBoardData(); // 이 부분은 아래와 같이 수정됨
  const {
    fetchKnowledge,
    visiblePosts,
    allPosts,
    loadMore,
    hasMore,
    loadingPosts,
    postsError,
    knowledgeError,
  } = useBoardData({ autoFetchKnowledge: false });
  const { crawlResults, crawling, crawlingStatus, testCrawl } = useCrawler(fetchKnowledge);
  const {
    isLoading,
    activeDomain,
    previewTemplate,
    templateError,
    fetchTemplatePreview,
    downloadTemplate,
  } = useTemplateService();
  // 데이터 로딩 부분은 useBoardData로 이동하여 제거함
  // fetchPostsData 제거

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
              <Button size="sm" variant="outline">하네스 운영</Button>
            </Link>
            <Link href="/settings">
              <Button size="sm" variant="outline">프로젝트 설정</Button>
            </Link>
            <Link href="/about">
              <Button size="sm" variant="outline">About</Button>
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
        templateError={templateError}
        onFetchPreview={fetchTemplatePreview}
        onDownload={downloadTemplate}
      />

      <main className="mx-auto max-w-7xl space-y-6 px-4 py-6">
        {/* [REMOVED: RecommendedSettingCard & LlmRouter] */}

        <BoardFilters
          query={query}
          selectedCategory={selectedCategory}
          selectedDomain={selectedDomain}
          onQueryChange={setQuery}
          onCategoryChange={setSelectedCategory}
          onDomainChange={setSelectedDomain}
        />

        <section className="space-y-4">
          {(postsError || knowledgeError) && (
            <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              데이터 로드 중 오류가 발생했습니다.
              {postsError ? ` posts: ${postsError}` : ""}
              {knowledgeError ? ` knowledge: ${knowledgeError}` : ""}
            </div>
          )}

          {loadingPosts ? (
            <div className="rounded-3xl border border-slate-200 bg-white p-8 text-center text-slate-500">
              운용 포스트를 불러오는 중입니다...
            </div>
          ) : filteredPosts.length > 0 ? (
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
