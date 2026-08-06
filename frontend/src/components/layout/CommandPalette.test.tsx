import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "@/lib/theme";
import { CommandPalette } from "./CommandPalette";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

function renderPalette(open: boolean, onClose: () => void) {
  return render(
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider>
          <CommandPalette open={open} onClose={onClose} />
        </ThemeProvider>
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe("CommandPalette", () => {
  it("hides when closed", () => {
    renderPalette(false, vi.fn());
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("shows commands and filters by query", () => {
    renderPalette(true, vi.fn());
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("运营总览")).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText("搜索页面、平台或操作…"), {
      target: { value: "评论" },
    });
    expect(screen.getByText("评论收件箱")).toBeInTheDocument();
    expect(screen.queryByText("运营总览")).not.toBeInTheDocument();
  });

  it("closes on Escape", () => {
    const onClose = vi.fn();
    renderPalette(true, onClose);
    fireEvent.keyDown(screen.getByPlaceholderText("搜索页面、平台或操作…"), {
      key: "Escape",
    });
    expect(onClose).toHaveBeenCalled();
  });
});
