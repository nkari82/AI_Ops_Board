import { useCallback, useState } from "react";
import { crawlGithubApi, crawlHnApi, crawlRedditApi } from "@/lib/api";

type CrawlResults = {
  reddit?: { title: string }[];
  github?: { name: string }[];
  hn?: { title: string }[];
};

export function useCrawler(onCrawlComplete?: () => void) {
  const [crawlResults, setCrawlResults] = useState<CrawlResults>({});
  const [crawling, setCrawling] = useState(false);
  const [crawlingStatus, setCrawlingStatus] = useState("대기 중");

  const testCrawl = useCallback(async () => {
    if (crawling) return;
    setCrawling(true);
    setCrawlingStatus("진행 중...");
    setCrawlResults({});
    try {
      await Promise.all([
        crawlRedditApi("LocalLLaMA", 5),
        crawlGithubApi(5),
        crawlHnApi(5),
      ]);
      setCrawlingStatus("작업 완료");
      onCrawlComplete?.();
    } catch (error) {
      const message = error instanceof Error ? error.message : "크롤링 요청 실패";
      console.error("Crawl test failed:", error);
      setCrawlingStatus(`실패: ${message}`);
    } finally {
      setCrawling(false);
    }
  }, [crawling, onCrawlComplete]);

  return { crawlResults, crawling, crawlingStatus, testCrawl };
}
