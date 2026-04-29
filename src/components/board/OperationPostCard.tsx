import React, { useMemo, useState } from "react";
import type { OperationPost } from "@/types";
import { Card, CardContent } from "@/components/ui/card";
import { DomainIcon } from "@/components/shared/DomainIcon";
import { MiniBlock } from "@/components/shared/MiniBlock";
import { CompareBox } from "@/components/shared/CompareBox";
import { riskClass, sourceLabel } from "@/lib/boardUtils";
import { cn } from "@/lib/utils";

interface OperationPostCardProps {
  post: OperationPost;
}

export function OperationPostCard({ post }: OperationPostCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const originalUrl = useMemo(() => {
    if (!post?.sources?.length) return null;
    const url = post.sources.find((s) => typeof s === "string" && /^https?:\/\//.test(s));
    return url ?? null;
  }, [post?.sources]);

  if (!post) return null;

  return (
    <Card 
      className="rounded-3xl border-slate-200 bg-white shadow-sm transition hover:-translate-y-0.5 hover:shadow-md cursor-pointer"
      onClick={() => setIsExpanded(!isExpanded)}
    >
      <CardContent className="p-5">
        <div className="mb-3 flex flex-wrap items-center gap-2 text-xs">
          {post.domain && (
            <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-1 text-slate-700">
              <DomainIcon domain={post.domain} /> {post.domain}
            </span>
          )}
          {post.category && <span className="rounded-full bg-blue-50 px-2.5 py-1 text-blue-700">{post.category}</span>}
          {post.docType && <span className="rounded-full bg-orange-50 px-2.5 py-1 text-orange-700">{post.docType}</span>}
          {post.techStack && post.techStack.map(tech => (
            <span key={tech} className="rounded-full bg-green-50 px-2.5 py-1 text-green-700">{tech}</span>
          ))}
          <span className="ml-auto rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 font-bold text-emerald-700">
            {post.score ?? 0}
          </span>
        </div>

        <div className="flex items-start justify-between gap-3">
          <h3 className="text-lg font-bold leading-snug">{post.titleKo || post.title}</h3>
          {originalUrl && (
            <a
              href={originalUrl}
              target="_blank"
              rel="noreferrer"
              className={cn(
                "shrink-0 rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-700",
                "hover:border-slate-300 hover:bg-slate-50"
              )}
              onClick={(e) => e.stopPropagation()}
            >
              원문 링크
            </a>
          )}
        </div>
        <p className={cn("mt-2 text-sm leading-6 text-slate-600", !isExpanded && "line-clamp-3")}>
          {post.summaryKo || post.summary || "요약이 없습니다."}
        </p>

        {isExpanded && (
          <div className="mt-4 space-y-3 border-t border-slate-100 pt-4">
            <div>
              <div className="text-xs font-bold uppercase tracking-wide text-slate-500">요약 전체</div>
              <div className="mt-1 whitespace-pre-wrap text-sm leading-6 text-slate-700">
                {post.summaryKo || post.summary || "요약이 없습니다."}
              </div>
            </div>
            <div>
              <div className="text-xs font-bold uppercase tracking-wide text-slate-500">원문</div>
              <div className="mt-1 whitespace-pre-wrap text-sm leading-6 text-slate-700">
                {post.content || "원문 내용이 없습니다."}
              </div>
            </div>
          </div>
        )}

        {isExpanded && (
          <>
            <div className="mt-4 grid gap-3 md:grid-cols-3">
              {post.rule && <MiniBlock title="Rule" value={post.rule} />}
              {post.skill && <MiniBlock title="Skill" value={post.skill} />}
              {post.agentRule && <MiniBlock title="AGENTS.md" value={post.agentRule} />}
            </div>

            {(post.badExample || post.goodExample) && (
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                {post.badExample && <CompareBox type="bad" title="나쁜 사용" text={post.badExample} />}
                {post.goodExample && <CompareBox type="good" title="좋은 사용" text={post.goodExample} />}
              </div>
            )}

            <div className="mt-4 rounded-2xl border border-slate-100 bg-slate-50 p-3">
              <div className="text-xs font-bold uppercase tracking-wide text-slate-500">바로 적용</div>
              <div className="mt-1 text-sm font-medium text-slate-800">{post.action}</div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

