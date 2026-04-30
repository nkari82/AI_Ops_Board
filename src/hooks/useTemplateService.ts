import { useCallback, useState } from "react";
import { downloadTemplateApi, generateOpsTemplateApi } from "@/lib/api";

export function useTemplateService() {
  const [template, setTemplate] = useState("");
  const [generating, setGenerating] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [activeDomain, setActiveDomain] = useState<string | null>(null);
  const [previewTemplate, setPreviewTemplate] = useState<string>("");
  const [templateError, setTemplateError] = useState<string | null>(null);

  const generateOpsTemplate = useCallback(async (domain: string) => {
    setGenerating(true);
    try {
      const data = await generateOpsTemplateApi(domain);
      setTemplate(data.template);
    } catch (e) {
      console.error("Template generation failed:", e);
    } finally {
      setGenerating(false);
    }
  }, []);

  const fetchTemplatePreview = useCallback(async (domain: string) => {
    setIsLoading(true);
    setTemplateError(null);
    setActiveDomain(domain);
    try {
      const data = await generateOpsTemplateApi(domain);
      setPreviewTemplate(data.template);
    } catch (e) {
      console.error("Template preview failed:", e);
      const message = e instanceof Error ? e.message : "템플릿 생성에 실패했습니다.";
      setTemplateError(message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const downloadTemplate = useCallback(async (domain: string) => {
    try {
      const blob = await downloadTemplateApi(domain);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${domain}-ops-template.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (e) {
      console.error("Template download failed:", e);
    }
  }, []);

  return {
    template,
    generating,
    isLoading,
    activeDomain,
    previewTemplate,
    templateError,
    generateOpsTemplate,
    fetchTemplatePreview,
    downloadTemplate,
  };
}
