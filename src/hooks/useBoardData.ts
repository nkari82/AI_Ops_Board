import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { KnowledgeCard, OperationPost } from "@/types";
import { ApiError, fetchKnowledgeApi, fetchOperationPostsApi } from "@/lib/api";
import { getCachedValue, setCachedValue } from "@/lib/runtimeCache";

const POSTS_CACHE_KEY = "board:posts";
const KNOWLEDGE_CACHE_KEY = "board:knowledge";
const CACHE_TTL_MS = 2 * 60 * 1000;

export function useBoardData(options?: { autoFetchKnowledge?: boolean }) {
  const autoFetchKnowledge = options?.autoFetchKnowledge ?? true;
  const [allPosts, setAllPosts] = useState<OperationPost[]>([]);
  const [knowledgeCards, setKnowledgeCards] = useState<KnowledgeCard[]>([]);
  const [visibleCount, setVisibleCount] = useState(10);
  const [loadingPosts, setLoadingPosts] = useState(false);
  const [loadingKnowledge, setLoadingKnowledge] = useState(false);
  const [postsError, setPostsError] = useState<string | null>(null);
  const [knowledgeError, setKnowledgeError] = useState<string | null>(null);

  const mountedRef = useRef(true);
  const postsReqSeqRef = useRef(0);
  const knowledgeReqSeqRef = useRef(0);
  const postsAbortRef = useRef<AbortController | null>(null);
  const knowledgeAbortRef = useRef<AbortController | null>(null);

  const fetchOperationPosts = useCallback(async () => {
    postsAbortRef.current?.abort();
    const controller = new AbortController();
    postsAbortRef.current = controller;

    const requestSeq = ++postsReqSeqRef.current;
    setLoadingPosts(true);
    setPostsError(null);

    try {
      const data = await fetchOperationPostsApi(controller.signal);
      if (!mountedRef.current || requestSeq !== postsReqSeqRef.current) return;

      const sortedData = [...data].sort(
        (a, b) => new Date(b.updatedAt || 0).getTime() - new Date(a.updatedAt || 0).getTime(),
      );
      setAllPosts(sortedData);
      setCachedValue(POSTS_CACHE_KEY, sortedData);
    } catch (error) {
      if (!mountedRef.current || requestSeq !== postsReqSeqRef.current) return;
      if (error instanceof ApiError && error.status === 408) return;
      const cachedPosts = getCachedValue<OperationPost[]>(POSTS_CACHE_KEY, CACHE_TTL_MS);
      if (cachedPosts && cachedPosts.length > 0) {
        setAllPosts(cachedPosts);
      }
      const message = error instanceof Error ? error.message : "운용 포스트 조회 실패";
      setPostsError(message);
      console.error("Posts fetch failed:", error);
    } finally {
      if (mountedRef.current && requestSeq === postsReqSeqRef.current) {
        setLoadingPosts(false);
      }
    }
  }, []);

  const fetchKnowledge = useCallback(async () => {
    knowledgeAbortRef.current?.abort();
    const controller = new AbortController();
    knowledgeAbortRef.current = controller;

    const requestSeq = ++knowledgeReqSeqRef.current;
    setLoadingKnowledge(true);
    setKnowledgeError(null);

    try {
      const data = await fetchKnowledgeApi(controller.signal);
      if (!mountedRef.current || requestSeq !== knowledgeReqSeqRef.current) return;
      setKnowledgeCards(data);
      setCachedValue(KNOWLEDGE_CACHE_KEY, data);
    } catch (error) {
      if (!mountedRef.current || requestSeq !== knowledgeReqSeqRef.current) return;
      if (error instanceof ApiError && error.status === 408) return;
      const cachedKnowledge = getCachedValue<KnowledgeCard[]>(KNOWLEDGE_CACHE_KEY, CACHE_TTL_MS);
      if (cachedKnowledge && cachedKnowledge.length > 0) {
        setKnowledgeCards(cachedKnowledge);
      }
      const message = error instanceof Error ? error.message : "지식 카드 조회 실패";
      setKnowledgeError(message);
      console.error("Knowledge fetch failed:", error);
    } finally {
      if (mountedRef.current && requestSeq === knowledgeReqSeqRef.current) {
        setLoadingKnowledge(false);
      }
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    const timer = setTimeout(() => {
      void fetchOperationPosts();
      if (autoFetchKnowledge) {
        void fetchKnowledge();
      }
    }, 0);

    return () => {
      clearTimeout(timer);
      mountedRef.current = false;
      postsAbortRef.current?.abort();
      knowledgeAbortRef.current?.abort();
    };
  }, [fetchOperationPosts, fetchKnowledge, autoFetchKnowledge]);

  const visiblePosts = useMemo(() => allPosts.slice(0, visibleCount), [allPosts, visibleCount]);
  const hasMore = visibleCount < allPosts.length;

  const loadMore = () => {
    setVisibleCount((prev) => prev + 10);
  };

  return {
    knowledgeCards,
    fetchKnowledge,
    visiblePosts,
    allPosts,
    loadMore,
    hasMore,
    loadingPosts,
    loadingKnowledge,
    postsError,
    knowledgeError,
  };
}
