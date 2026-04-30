import { describe, it, expect, beforeEach, vi } from "vitest";
import { ApiError, fetchOperationPostsApi } from "@/lib/api";

const fetchMock = vi.fn<Parameters<typeof fetch>, ReturnType<typeof fetch>>();
global.fetch = fetchMock;

describe("ApiClient Error Handling", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should throw ApiError on 500 status", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ error: "Internal error" }), { status: 500 })
    );

    await expect(fetchOperationPostsApi()).rejects.toThrow(ApiError);
  });

  it("should extract detail field from error response", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "Invalid token" }), { status: 401 })
    );

    try {
      await fetchOperationPostsApi();
      expect.fail("Should have thrown");
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      expect((e as ApiError).message).toContain("Invalid token");
    }
  });

  it("should handle missing detail field gracefully", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ error: "Something went wrong" }), { status: 500 })
    );

    try {
      await fetchOperationPostsApi();
      expect.fail("Should have thrown");
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      expect((e as ApiError).message).toBeDefined();
      expect((e as ApiError).message).not.toContain("undefined");
    }
  });

  it("should timeout after DEFAULT_TIMEOUT_MS", async () => {
    fetchMock.mockImplementationOnce(
      () => new Promise(() => {})
    );

    const promise = fetchOperationPostsApi();
    await expect(promise).rejects.toThrow("시간 초과");
  });

  it("should handle network errors", async () => {
    fetchMock.mockRejectedValueOnce(new TypeError("Failed to fetch"));

    await expect(fetchOperationPostsApi()).rejects.toThrow(ApiError);
  });

  it("should handle malformed JSON response", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response("not json", { status: 200 })
    );

    await expect(fetchOperationPostsApi()).rejects.toThrow();
  });

  it("should set correct status code on ApiError", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "Not found" }), { status: 404 })
    );

    try {
      await fetchOperationPostsApi();
      expect.fail("Should have thrown");
    } catch (e) {
      expect((e as ApiError).status).toBe(404);
    }
  });
});
