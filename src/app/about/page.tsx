import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-950">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4">
          <div>
            <h1 className="text-2xl font-bold">About AI Ops Board</h1>
            <p className="text-sm text-slate-600">하네스 운영 지식을 수집·가공·운영 가능한 형태로 제공하는 프로젝트</p>
          </div>
          <div className="flex items-center gap-2">
            <Link href="/recommendations"><Button variant="outline">하네스 운영</Button></Link>
            <Link href="/settings"><Button variant="outline">프로젝트 설정</Button></Link>
            <Link href="/"><Button variant="outline">보드</Button></Link>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl space-y-4 px-4 py-6">
        <section className="rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="text-lg font-semibold">프로젝트 목적</h2>
          <p className="mt-2 text-sm leading-6 text-slate-700">
            AI Ops Board는 여러 소스(Reddit, GitHub, Hacker News, YouTube, GeekNews)에서 하네스 운영 관련 파편 지식을 자동 수집하고,
            LLM 분석을 통해 운영 가능한 데이터로 정제하여 팀이 실제 운영에 재사용할 수 있도록 만드는 지능형 Ops 지원 플랫폼입니다.
          </p>
        </section>

        <section className="grid gap-4 md:grid-cols-2">
          <div className="rounded-2xl border border-slate-200 bg-white p-5">
            <h3 className="text-base font-semibold">핵심 파이프라인</h3>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
              <li>Crawler → Ingest → Content Analyzer → Postgres(pgvector)</li>
              <li>운영 지표(health/admin/crawl health)로 품질·안정성 모니터링</li>
              <li>도메인별 하네스 운영 추천 셋팅과 템플릿 산출물 제공</li>
            </ul>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-5">
            <h3 className="text-base font-semibold">실사용 기준</h3>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
              <li>release/smoke gate 통과 (build, compile, API smoke)</li>
              <li>소스별 crawl health와 LLM 상태가 settings에서 관측 가능</li>
              <li>실패 시 원인/복구 절차를 runbook으로 연결</li>
            </ul>
          </div>
        </section>
      </main>
    </div>
  );
}
