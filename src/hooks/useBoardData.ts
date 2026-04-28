import { useCallback, useEffect, useState } from "react";
import type { Domain, UserPost } from "@/types";
import { fetchKnowledgeApi, fetchOperationPostsApi } from "@/lib/api";

export function useBoardData() {
  const [userPosts, setUserPosts] = useState<UserPost[]>([]);
  const [knowledgeCards, setKnowledgeCards] = useState<unknown[]>([]);

  const fetchPosts = useCallback(async () => {
    try {
      const data = await fetchOperationPostsApi();
      setUserPosts(data);
    } catch (e) {
      console.error("Posts fetch failed:", e);
    }
  }, []);

  const fetchKnowledge = useCallback(async () => {
    try {
      const data = await fetchKnowledgeApi();
      setKnowledgeCards(data);
    } catch (e) {
      console.error("Knowledge fetch failed:", e);
    }
  }, []);

  useEffect(() => {
    fetchPosts();
    fetchKnowledge();
  }, [fetchPosts, fetchKnowledge]);

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

  return { userPosts, knowledgeCards, fetchPosts, fetchKnowledge, registerUserPost };
}
