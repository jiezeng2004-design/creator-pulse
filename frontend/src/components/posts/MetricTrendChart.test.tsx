import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MetricTrendChart } from "./MetricTrendChart";
import type { MetricSnapshot } from "@/types";

function snapshot(
  id: number,
  capturedAt: string,
  values: Partial<MetricSnapshot>,
): MetricSnapshot {
  return {
    id,
    post_id: 7,
    captured_at: capturedAt,
    view_count: null,
    impression_count: null,
    like_count: null,
    favorite_count: null,
    share_count: null,
    repost_count: null,
    comment_count: null,
    ...values,
  };
}

describe("MetricTrendChart", () => {
  it("explains when no snapshots exist", () => {
    render(<MetricTrendChart snapshots={[]} />);
    expect(screen.getByText(/暂无历史快照/)).toBeInTheDocument();
  });

  it("explains when every metric is unavailable", () => {
    render(
      <MetricTrendChart
        snapshots={[snapshot(1, "2026-08-01T00:00:00Z", {})]}
      />,
    );
    expect(screen.getByText(/尚未提供可绘制的指标/)).toBeInTheDocument();
  });

  it("shows summary values and lets the user change metrics", () => {
    render(
      <MetricTrendChart
        snapshots={[
          snapshot(1, "2026-08-01T00:00:00Z", {
            view_count: 100,
            like_count: 10,
          }),
          snapshot(2, "2026-08-02T00:00:00Z", {
            view_count: 150,
            like_count: 25,
          }),
        ]}
      />,
    );

    expect(screen.getByText("最新浏览")).toBeInTheDocument();
    expect(screen.getByText("+50")).toBeInTheDocument();
    expect(screen.getByRole("img")).toHaveAccessibleName(/浏览历史趋势/);

    fireEvent.change(screen.getByLabelText("趋势指标"), {
      target: { value: "like_count" },
    });

    expect(screen.getByText("最新点赞")).toBeInTheDocument();
    expect(screen.getByText("+15")).toBeInTheDocument();
  });

  it("does not connect a line across a missing snapshot", () => {
    const { container } = render(
      <MetricTrendChart
        snapshots={[
          snapshot(1, "2026-08-01T00:00:00Z", { view_count: 100 }),
          snapshot(2, "2026-08-02T00:00:00Z", { view_count: null }),
          snapshot(3, "2026-08-03T00:00:00Z", { view_count: 180 }),
        ]}
      />,
    );

    expect(container.querySelectorAll("circle")).toHaveLength(2);
    expect(container.querySelectorAll("polyline")).toHaveLength(0);
  });
});
