import React, { useMemo, useState, useCallback } from "react";
import type { BoardCategory, Domain } from "@/types";
import { models, recommendedSettings, agentsTemplate } from "@/lib/constants";
import { fetchOperationPostsApi } from "@/lib/api";
import { useBoardData } from "@/hooks/useBoardData";
import { useCrawler } from "@/hooks/useCrawler";
import { useTemplateService } from "@/hooks/useTemplateService";
import { RecommendedSettingCard } from "@/components/recommended/RecommendedSettingCard";
import { LlmRouter } from "@/components/llm/LlmRouter";
import { Metric } from "@/components/shared/Metric";
import { BoardFilters } from "@/components/board/BoardFilters";
import { OperationPostCard } from "@/components/board/OperationPostCard";
import { UserBoard } from "@/components/board/UserBoard";
import { CrawlResultsPanel } from "@/components/crawler/CrawlResultsPanel";
import { TemplateService } from "@/components/template/TemplateService";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  AlertTriangle,
  Flame,
  Globe2,
  Layers3,
  RefreshCw,
  ShieldAlert,
  Sparkles,
  UserRound,
} from "lucide-react";

export default function AiOpsBoard() {
  const [query, setQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<BoardCategory | "전체">("전체");
  const [selectedDomain, setSelectedDomain] = useState<Domain | "전체">("전체");
  const [selectedModel, setSelectedModel] = useState(models[0].id);
  const [activeSetting, setActiveSetting] = useState<Domain>("Unity");

  const { userPosts, fetchKnowledge, registerUserPost } = useBoardData();
  const { crawlResults, crawling, crawlingStatus, testCrawl } = useCrawler(fetchKnowledge);
  const {
    template,
    generating,
    isLoading,
    activeDomain,
    previewTemplate,
    generateOpsTemplate,
    fetchTemplatePreview,
    downloadTemplate,
  } = useTemplateService();
  const [operationPosts, setOperationPosts] = useState<any[]>([]);

  // ... (existing state)

  const fetchPostsData = useCallback(async () => {
    try {
      const data = await fetchOperationPostsApi();
      setOperationPosts(data);
    } catch (e) {
      console.error("Operation posts fetch failed:", e);
    }
  }, []);

  React.useEffect(() => {
    fetchPostsData();
    fetchKnowledge();
  }, [fetchPostsData, fetchKnowledge]);

  // ... (existing logic)

  const filteredPosts = useMemo(() => {
    const q = query.trim().toLowerCase();
    return operationPosts.filter((post) => {
      const categoryOk = selectedCategory === "전체" || post.category === selectedCategory;
      const domainOk = selectedDomain === "전체" || post.domain === selectedDomain;
      const queryOk =
        q.length === 0 ||
        [post.title, post.summary, post.rule, post.skill, post.agentRule, post.domain, post.category, ...post.tags]
          .filter(Boolean)
          .join(" ")
          .toLowerCase()
          .includes(q);
      return categoryOk && domainOk && queryOk;
    });
  }, [query, selectedCategory, selectedDomain]);

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
              {crawling ? "크롤링 중..." : "크롤링 테스트"}
            </Button>
            <span className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-white px-3 py-1">
              <Flame className="h-3.5 w-3.5" /> 추천 셋팅 하루 1회
            </span>
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
        <section className="grid gap-4 lg:grid-cols-[1.25fr_0.75fr]">
          <RecommendedSettingCard
            settings={recommendedSettings}
            activeSetting={activeSetting}
            onSelectSetting={setActiveSetting}
          />
          <LlmRouter
            models={models}
            selectedModel={selectedModel}
            onSelectModel={setSelectedModel}
          />
        </section>

        <section className="grid gap-4 md:grid-cols-4">
          <Metric icon={<Globe2 className="h-5 w-5" />} label="자동 수집 보드" value="크롤링 + AI" caption="유저 게시판 제외" />
          <Metric icon={<UserRound className="h-5 w-5" />} label="유저 게시판" value="수동 입력" caption="자동 수집 없음" />
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

        <section className="grid gap-4 lg:grid-cols-[1fr_380px]">
          <div className="space-y-4">
            {filteredPosts.length > 0 ? (
              filteredPosts.map((post) => (
                <OperationPostCard key={post.id} post={post} />
              ))
            ) : (
              <div className="rounded-3xl border border-slate-200 bg-white p-8 text-center text-slate-500">
                표시할 운용 포스트가 없습니다. 크롤링을 실행하거나 필터를 조정하세요.
              </div>
            )}
          </div>

          <aside className="space-y-4">
            <UserBoard
              userPosts={userPosts}
              activeDomain={activeSetting}
              onRegister={registerUserPost}
            />
            <TemplateService
              agentsTemplate={agentsTemplate}
              activeDomain={activeSetting}
              template={template}
              generating={generating}
              onGenerate={generateOpsTemplate}
            />
            <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
              <CardContent className="p-5 text-sm leading-6 text-slate-700">
                <h2 className="flex items-center gap-2 text-lg font-bold text-slate-950">
                  <AlertTriangle className="h-5 w-5 text-amber-500" /> Production 설계
                </h2>
                <ul className="mt-3 list-disc space-y-1 pl-5">
                  <li>FastAPI + PostgreSQL</li>
                  <li>Celery/RQ 크롤러</li>
                  <li>유저 게시판은 수동 입력만 허용</li>
                  <li>그 외 보드는 웹 크롤링 + AI 요약 + 축적 + 합성 데이터</li>
                  <li>LLM Router: 무료/로컬/유료 모델 역할 분리</li>
                  <li>추천 셋팅은 분야별 하루 1회 생성</li>
                </ul>
              </CardContent>
            </Card>
          </aside>
        </section>
      </main>
    </div>
  );
}
