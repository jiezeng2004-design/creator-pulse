import clsx from "clsx";

type PlatformIconProps = {
  platform: string;
  size?: "sm" | "md" | "lg";
  className?: string;
};

const sizeClass = {
  sm: "h-8 w-8",
  md: "h-10 w-10",
  lg: "h-12 w-12",
} as const;

// Font size must scale with the icon box; percentage font sizes resolve
// against the inherited text size instead, making the wordmark too small.
const wordmarkClass = {
  sm: "text-[10px]",
  md: "text-[13px]",
  lg: "text-[15px]",
} as const;
/**
 * Local brand marks keep platform identity visible even when the API is down.
 * X uses the official glyph; the domestic platforms use their recognizable
 * official Chinese wordmarks rather than invented generic illustrations.
 */
export function PlatformIcon({ platform, size = "md", className }: PlatformIconProps) {
  return (
    <span
      className={clsx(
        "inline-flex shrink-0 items-center justify-center overflow-hidden rounded-[13px]",
        sizeClass[size],
        wordmarkClass[size],
        platform === "x" && "bg-[#050505] text-white",
        platform === "zhihu" && "bg-[#06f] text-white",
        platform === "toutiao" && "bg-[#f02d2d] text-white",
        platform === "xiaohongshu" && "bg-[#ff2442] text-white",
        !["x", "zhihu", "toutiao", "xiaohongshu"].includes(platform) &&
          "bg-ink-900/10 text-ink-700",
        className,
      )}
      aria-label={`${platform} 平台图标`}
    >
      {platform === "x" && (
        <svg viewBox="0 0 24 24" className="h-[52%] w-[52%] fill-current" aria-hidden>
          <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24h-6.657l-5.214-6.817-5.967 6.817H1.681l7.73-8.835L1.255 2.25H8.08l4.713 6.231 5.451-6.231Zm-1.161 17.52h1.833L7.084 4.126H5.117L17.083 19.77Z" />
        </svg>
      )}
      {platform === "zhihu" && <span className="font-sans font-black">知乎</span>}
      {platform === "toutiao" && <span className="font-sans font-black">头条</span>}
      {platform === "xiaohongshu" && <span className="font-sans text-[0.85em] font-black">小红书</span>}
      {!['x', 'zhihu', 'toutiao', 'xiaohongshu'].includes(platform) && (
        <span className="text-xs font-bold">?</span>
      )}
    </span>
  );
}
