export const PLATFORMS = [
  { id: "x", label: "X" },
  { id: "zhihu", label: "知乎" },
  { id: "toutiao", label: "今日头条" },
  { id: "xiaohongshu", label: "小红书" },
] as const;

export const QUICK_PLATFORMS = [
  { id: "zhihu", label: "知乎" },
  { id: "toutiao", label: "头条" },
  { id: "xiaohongshu", label: "小红书" },
  { id: "x", label: "X" },
] as const;

export const STATUS_TABS = [
  { value: "", label: "全部" },
  { value: "new", label: "新评论" },
  { value: "pending", label: "待处理" },
  { value: "handled", label: "已处理" },
  { value: "ignored", label: "已忽略" },
] as const;

export const PLATFORM_LABEL: Record<string, string> = {
  x: "X",
  zhihu: "知乎",
  toutiao: "今日头条",
  xiaohongshu: "小红书",
};

export const PLATFORM_ACCENT: Record<string, string> = {
  x: "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900",
  zhihu: "bg-blue-600 text-white",
  toutiao: "bg-red-600 text-white",
  xiaohongshu: "bg-rose-500 text-white",
};

/** Raw platform brand colors used for accent bars and inline highlights. */
export const PLATFORM_COLOR: Record<string, string> = {
  x: "#111827",
  zhihu: "#056de8",
  toutiao: "#e63a3a",
  xiaohongshu: "#ff2442",
};

export function platformColor(platform: string): string {
  return PLATFORM_COLOR[platform] || "#7a807b";
}
