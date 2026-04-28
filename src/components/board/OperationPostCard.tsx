import React from "react";
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
  return (
    <Card className="rounded-3xl border-slate-200 bg-white shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
      <CardContent className="p-5">
        <div className="mb-3 flex flex-wrap items-center gap-2 text-xs">
          <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-1 text-slate-700">
            <DomainIcon domain={post.domain} /> {post.domain}
          </span>
          <span className="rounded-full bg-blue-50 px-2.5 py-1 text-blue-700">{post.category}</span>
          <span className="rounded-full bg-purple-50 px-2.5 py-1 text-purple-700">
            {sourceLabel(post.sourceKind)}
          </span>
          <span className={cn("rounded-full border px-2.5 py-1", riskClass(post.risk))}>
            risk {post.risk}
          </span>
          <span className="ml-auto rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 font-bold text-emerald-700">
            {post.score}
          </span>
        </div>

        <h3 className="text-lg font-bold leading-snug">{post.title}</h3>
        <p className="mt-2 text-sm leading-6 text-slate-600">{post.summary}</p>

        <div className="mt-3 flex flex-wrap gap-1.5 text-xs">
          {post.sources.map((source) => (
            <span key={source} className="rounded-full bg-slate-100 px-2 py-0.5 text-slate-600">
              {source}
            </span>
          ))}
        </div>

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
      </CardContent>
    </Card>
  );
}
