import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-950">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
          <div>
            <h1 className="text-2xl font-bold">About AI Ops Board</h1>
            <p className="text-sm text-slate-600">크롤링부터 추천 템플릿까지, 하네스 운영 지식을 실제 실행 가능한 형태로 만드는 플랫폼</p>
          </div>
          <div className="flex items-center gap-2">
            <Link href="/recommendations"><Button variant="outline">하네스 운영</Button></Link>
            <Link href="/settings"><Button variant="outline">프로젝트 설정</Button></Link>
            <Link href="/"><Button variant="outline">보드</Button></Link>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-4 px-4 py-6">
        <section className="rounded-2xl border border-blue-200 bg-blue-50 p-5">
          <h2 className="text-lg font-semibold text-blue-900">이 프로젝트를 쉽게 설명하면</h2>
          <p className="mt-2 text-sm leading-6 text-blue-900/90">
            AI Ops Board는 인터넷에 흩어진 운영 팁을 자동으로 모으고, 노이즈를 걸러서,
            팀이 바로 복붙해서 쓸 수 있는 <span className="font-semibold">운영 템플릿(.opencode / .claude)</span>으로 바꿔주는 도구입니다.
            즉, &quot;좋은 글을 찾는 시간&quot;을 줄이고 &quot;실행 가능한 운영 설정&quot;을 빠르게 얻는 것이 핵심입니다.
          </p>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="text-lg font-semibold">프로젝트 요지</h2>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm leading-6 text-slate-700">
            <li>여러 소스에서 하네스/운영 관련 지식을 자동 수집</li>
            <li>LLM + 규칙 기반 정제로 신뢰 가능한 추천 신호 추출</li>
            <li>도메인별 추천 설정(모델 라우팅, 워크플로우, MCP/Rules) 생성</li>
            <li>추천 결과를 공식 구조에 맞는 템플릿 ZIP으로 즉시 배포 가능</li>
          </ul>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="text-lg font-semibold">아키텍처(상세)</h2>
          <div className="mt-3 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <h3 className="text-sm font-semibold">1) Ingestion Layer</h3>
              <p className="mt-2 text-xs leading-5 text-slate-700">
                Reddit / GitHub / Hacker News / YouTube / GeekNews 크롤러가 원천 데이터를 수집합니다.
                비동기 백그라운드 태스크(Celery)로 장시간 작업을 처리합니다.
              </p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <h3 className="text-sm font-semibold">2) Analysis Layer</h3>
              <p className="mt-2 text-xs leading-5 text-slate-700">
                콘텐츠 분석기와 LLM 라우터가 요약/분류/리스크/태그를 생성합니다.
                잘못된 신호(실패 문자열, 비정상 피드백 등)를 필터링해 데이터 오염을 줄입니다.
              </p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <h3 className="text-sm font-semibold">3) Recommendation Layer</h3>
              <p className="mt-2 text-xs leading-5 text-slate-700">
                도메인별 게시글 집계를 기반으로 모델/워크플로우/스킬 후보를 추천합니다.
                중복 긍정 신호 편향 완화, 피드백 검증, 캐시 신선도 가드를 적용합니다.
              </p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <h3 className="text-sm font-semibold">4) Template Layer</h3>
              <p className="mt-2 text-xs leading-5 text-slate-700">
                추천 결과를 `.opencode` / `.claude` 구조의 템플릿 ZIP으로 생성합니다.
                운영팀은 다운로드 후 프로젝트에 바로 적용할 수 있습니다.
              </p>
            </div>
          </div>
        </section>

        <section className="grid gap-4 md:grid-cols-2">
          <div className="rounded-2xl border border-slate-200 bg-white p-5">
            <h3 className="text-base font-semibold">요청 흐름 (Runtime Flow)</h3>
            <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm text-slate-700">
              <li>크롤링 태스크 실행 → 상태 추적 API로 진행률 확인</li>
              <li>분석 결과를 DB(PostgreSQL)로 적재</li>
              <li>추천 API가 도메인별 설정 후보 계산</li>
              <li>템플릿 API가 ZIP 번들 생성 후 다운로드</li>
            </ol>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-5">
            <h3 className="text-base font-semibold">품질 게이트 (Quality Gates)</h3>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
              <li>정적 검증: ESLint, TypeScript, Python compile</li>
              <li>기능 검증: API smoke / deep smoke / strict deep smoke</li>
              <li>회귀 검증: 핵심 pytest(리스크 분류, strict smoke 동작 등)</li>
              <li>릴리즈 전 `release:checks`, `release:full:deep` 계열 통과</li>
            </ul>
          </div>
        </section>
      </main>
    </div>
  );
}
