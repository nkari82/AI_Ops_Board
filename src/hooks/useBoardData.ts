import { useCallback, useEffect, useState } from "react";
import type { Domain, UserPost } from "@/types";
import { fetchKnowledgeApi } from "@/lib/api";

const INITIAL_USER_POSTS: UserPost[] = [
  {
    id: 101,
    title: "3090 2장으로 로컬 LLM 탐색 모델 돌리는 팁",
    body: "Qwen 계열을 OpenCode 탐색/요약용으로 쓰고 Claude는 최종 리뷰만 쓰는 구성이 제일 안정적이었다.",
    author: "dev01",
    domain: "로컬 LLM",
    votes: 21,
    createdAt: "오늘 11:30",
    tags: ["3090", "Qwen", "OpenCode"],
    sourceKind: "manual_user_input",
  },
  {
    id: 102,
    title: "Unity 프로젝트에서 AGENTS.md 짧게 줄인 후기",
    body: "규칙을 영어 1줄 + 한국어 설명 1줄로 줄였더니 반복 설명이 줄고 결과가 더 안정적이었다.",
    author: "client-dev",
    domain: "Unity",
    votes: 14,
    createdAt: "어제 22:10",
    tags: ["Unity", "AGENTS.md", "GC"],
    sourceKind: "manual_user_input",
  },
];

export function useBoardData() {
  const [userPosts, setUserPosts] = useState<UserPost[]>(INITIAL_USER_POSTS);
  const [knowledgeCards, setKnowledgeCards] = useState<unknown[]>([]);

  const fetchKnowledge = useCallback(async () => {
    try {
      const data = await fetchKnowledgeApi();
      setKnowledgeCards(data);
    } catch (e) {
      console.error("Knowledge fetch failed:", e);
    }
  }, []);

  useEffect(() => {
    fetchKnowledge();
  }, [fetchKnowledge]);

  const registerUserPost = useCallback(
    (title: string, body: string, domain: Domain) => {
      if (!title || !body) return;
      const newPost: UserPost = {
        id: Date.now(),
        title,
        body,
        author: "current-user",
        domain,
        votes: 0,
        createdAt: new Date().toLocaleTimeString(),
        tags: [],
        sourceKind: "manual_user_input",
      };
      setUserPosts((prev) => [newPost, ...prev]);
    },
    []
  );

  return { userPosts, knowledgeCards, fetchKnowledge, registerUserPost };
}
