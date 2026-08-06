import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Badge } from "./Badge";

describe("Badge", () => {
  it("renders children text", () => {
    render(<Badge>Hello</Badge>);
    expect(screen.getByText("Hello")).toBeInTheDocument();
  });

  it("renders as a span element", () => {
    render(<Badge>Tag</Badge>);
    const badge = screen.getByText("Tag");
    expect(badge.tagName).toBe("SPAN");
  });

  it("applies default tone class", () => {
    render(<Badge>Default</Badge>);
    const badge = screen.getByText("Default");
    expect(badge.className).toContain("text-ink-600");
  });

  it("applies success tone class", () => {
    render(<Badge tone="success">OK</Badge>);
    const badge = screen.getByText("OK");
    expect(badge.className).toContain("text-accent-green");
  });

  it("applies warn tone class", () => {
    render(<Badge tone="warn">Warning</Badge>);
    const badge = screen.getByText("Warning");
    expect(badge.className).toContain("text-accent-amber");
  });

  it("applies danger tone class", () => {
    render(<Badge tone="danger">Error</Badge>);
    const badge = screen.getByText("Error");
    expect(badge.className).toContain("text-accent-rose");
  });

  it("applies info tone class", () => {
    render(<Badge tone="info">Info</Badge>);
    const badge = screen.getByText("Info");
    expect(badge.className).toContain("text-brand-600");
  });

  it("applies mock tone class", () => {
    render(<Badge tone="mock">Mock</Badge>);
    const badge = screen.getByText("Mock");
    expect(badge.className).toContain("text-[#7c3aed]");
  });
});
