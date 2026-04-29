import { useCallback, useEffect, useState, useMemo } from "react";
import type { KnowledgeCard, OperationPost } from "@/types";
import { fetchKnowledgeApi, fetchOperationPostsApi } from "@/lib/api";

export function useBoardData() {
  const [allPosts, setAllPosts] = useState<OperationPost[]>([]);
  const [knowledgeCards, setKnowledgeCards] = useState<KnowledgeCard[]>([]);
  const [visibleCount, setVisibleCount] = useState(10);

  const fetchOperationPosts = useCallback(async () => {
    try {
      const data = await fetchOperationPostsApi();
      const sortedData = [...data].sort((a, b) => 
        new Date(b.updatedAt || 0).getTime() - new Date(a.updatedAt || 0).getTime()
      );
      setAllPosts(sortedData);
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
    fetchOperationPosts();
    fetchKnowledge();
  }, [fetchOperationPosts, fetchKnowledge]);

  const visiblePosts = useMemo(() => allPosts.slice(0, visibleCount), [allPosts, visibleCount]);
  const hasMore = visibleCount < allPosts.length;

  const loadMore = () => {
    setVisibleCount((prev) => prev + 10);
  };

  return { knowledgeCards, fetchKnowledge, visiblePosts, allPosts, loadMore, hasMore };
}
