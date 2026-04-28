import React, { useState } from "react";
import type { Domain, UserPost } from "@/types";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { BookOpen } from "lucide-react";

interface UserBoardProps {
  userPosts: UserPost[];
  activeDomain: Domain;
  onRegister: (title: string, body: string, domain: Domain) => void;
}

export function UserBoard({ userPosts, activeDomain, onRegister }: UserBoardProps) {
  const [draftTitle, setDraftTitle] = useState("");
  const [draftBody, setDraftBody] = useState("");

  const handleRegister = () => {
    if (!draftTitle || !draftBody) return;
    onRegister(draftTitle, draftBody, activeDomain);
    setDraftTitle("");
    setDraftBody("");
  };

  return (
    <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
      <CardContent className="p-5">
        <h2 className="flex items-center gap-2 text-lg font-bold">
          <BookOpen className="h-5 w-5 text-emerald-600" /> 유저 게시판
        </h2>
        <p className="mt-1 text-sm leading-6 text-slate-600">
          이 영역만 수동 입력 전용이다. 자동 크롤링/AI 합성 없이 실제 사용자 경험을 남긴다.
        </p>
        <div className="mt-4 grid gap-2">
          <input
            value={draftTitle}
            onChange={(e) => setDraftTitle(e.target.value)}
            placeholder="제목"
            className="h-10 rounded-2xl border border-slate-200 bg-slate-50 px-3 text-sm outline-none focus:ring-2 focus:ring-blue-500"
          />
          <textarea
            value={draftBody}
            onChange={(e) => setDraftBody(e.target.value)}
            placeholder="실전 운영 팁 작성"
            className="min-h-24 rounded-2xl border border-slate-200 bg-slate-50 p-3 text-sm outline-none focus:ring-2 focus:ring-blue-500"
          />
          <Button className="rounded-2xl" onClick={handleRegister}>
            등록
          </Button>
        </div>
        <div className="mt-4 space-y-3">
          {userPosts.map((post) => (
            <div key={post.id} className="rounded-2xl border border-slate-100 bg-slate-50 p-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="font-semibold">{post.title}</div>
                  <div className="mt-1 text-xs text-slate-500">
                    {post.author} · {post.createdAt}
                  </div>
                </div>
                <span className="rounded-full bg-emerald-50 px-2 py-1 text-xs text-emerald-700">수동 입력</span>
              </div>
              <p className="mt-2 text-sm leading-6 text-slate-600">{post.body}</p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {post.tags.map((tag) => (
                  <span key={tag} className="rounded-full bg-white px-2 py-0.5 text-xs text-slate-600">
                    #{tag}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
