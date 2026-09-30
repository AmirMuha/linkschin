import React from 'react'

export function SkeletonGrid({ count = 8 }: { count?: number }) {
  return (
    <div
      className="masonry columns-1 sm:columns-2 md:columns-3 lg:columns-4 gap-6 w-full"
      role="status"
      aria-label="در حال بارگذاری نتایج"
    >
      <span className="sr-only">در حال بارگذاری نتایج...</span>
      {Array.from({ length: count }).map((_, index) => (
        <div
          key={index}
          className="rounded-2xl bg-zinc-900/60 border border-zinc-800/80 p-4 flex flex-col gap-4 animate-pulse overflow-hidden shadow-lg"
        >
          {/* Poster / Thumbnail Placeholder */}
          <div className="w-full aspect-[2/3] bg-zinc-800/70 rounded-xl" />

          {/* Title and tags placeholders */}
          <div className="flex flex-col gap-2.5">
            <div className="h-5 bg-zinc-800 rounded-md w-3/4" />
            <div className="h-4 bg-zinc-800/60 rounded-md w-1/2" />
          </div>

          {/* Badges / Download trigger placeholder */}
          <div className="mt-auto pt-2 flex items-center justify-between gap-2 border-t border-zinc-800/60">
            <div className="h-6 bg-zinc-800/80 rounded-full w-16" />
            <div className="h-8 bg-zinc-800 rounded-lg w-24" />
          </div>
        </div>
      ))}
    </div>
  )
}
