import { describe, expect, it, vi } from "vitest";
import { api } from "../api/client";

vi.stubGlobal("fetch", vi.fn());

describe("api client", () => {
  it("health returns status", async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ status: "ok" }),
    } as Response);
    const res = await api.health();
    expect(res.status).toBe("ok");
  });

  it("platforms returns array", async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve([{ platform: "x", label: "X" }]),
    } as Response);
    const res = await api.platforms();
    expect(res).toHaveLength(1);
  });

  it("throws on non-ok response", async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: false,
      status: 404,
      statusText: "Not Found",
      json: () => Promise.resolve({ detail: "not found" }),
    } as Response);
    await expect(api.health()).rejects.toThrow("not found");
  });

  it("posts builds query params correctly", async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({ page: 1, page_size: 20, total: 0, items: [] }),
    } as Response);
    await api.posts({ page: "2", platform: "zhihu" });
    expect(fetch).toHaveBeenCalledWith(
      "/api/posts?page=2&platform=zhihu",
      expect.objectContaining({ headers: expect.anything() }),
    );
  });

  it("loads metric snapshots for one post", async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve([
          {
            id: 1,
            post_id: 42,
            captured_at: "2026-08-01T00:00:00Z",
            view_count: 120,
          },
        ]),
    } as Response);

    const result = await api.postMetrics(42);

    expect(fetch).toHaveBeenCalledWith(
      "/api/posts/42/metrics",
      expect.objectContaining({ headers: expect.anything() }),
    );
    expect(result[0]?.view_count).toBe(120);
  });
});
