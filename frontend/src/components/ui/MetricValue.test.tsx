import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MetricValue } from "./MetricValue";

describe("MetricValue", () => {
  it("renders formatted number", () => {
    render(<MetricValue value={1234} />);
    expect(screen.getByText("1,234")).toBeInTheDocument();
  });

  it("renders compact format", () => {
    render(<MetricValue value={15000} compact />);
    expect(screen.getByText("1.5万")).toBeInTheDocument();
  });

  it("renders 'not available' for null", () => {
    render(<MetricValue value={null} />);
    expect(screen.getByText("暂不可用")).toBeInTheDocument();
  });

  it("renders 'not available' for undefined", () => {
    render(<MetricValue value={undefined} />);
    expect(screen.getByText("暂不可用")).toBeInTheDocument();
  });

  it("applies custom className", () => {
    render(<MetricValue value={42} className="custom-class" />);
    const span = screen.getByText("42");
    expect(span.className).toContain("custom-class");
  });
});
