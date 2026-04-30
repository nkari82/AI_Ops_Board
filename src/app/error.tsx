"use client";

import { useEffect } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Global app error:", error);
  }, [error]);

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-16 text-slate-950">
      <div className="mx-auto max-w-2xl rounded-2xl border border-red-200 bg-white p-6">
        <h1 className="text-xl font-bold text-red-700">예상치 못한 오류가 발생했습니다</h1>
        <p className="mt-2 text-sm text-slate-700">
          일시적 문제일 수 있습니다. 다시 시도하거나 보드로 돌아가 상태를 확인해 주세요.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button onClick={reset}>다시 시도</Button>
          <Link href="/">
            <Button variant="outline">보드로 이동</Button>
          </Link>
          <Link href="/settings">
            <Button variant="outline">프로젝트 설정</Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
