'use client'

import React, { useState } from 'react'
import type { MediaItem } from '@/types/media'
import { Gamepad2, HardDrive, Tag, ExternalLink } from 'lucide-react'
import { PasswordPill } from './PasswordPill'
import { GamePartList } from './GamePartList'
import { TechnicalText } from '@/components/ui/TechnicalText'

interface GameCardProps {
  item: MediaItem
}

export function GameCard({ item }: GameCardProps) {
  const [imageError, setImageError] = useState(false)
  // A post can ship several archives (an exFAT set and a PKG set), each numbered
  // from 1. Only the first is summarised in the header; all of them are listed.
  const primaryRelease = item.game_releases?.[0]
  const otherReleases = item.game_releases?.slice(1) ?? []

  return (
    <article
      className="group relative flex flex-col rounded-3xl bg-zinc-900/70 border border-zinc-800/80 hover:border-zinc-700/80 p-4 transition-all hover:shadow-2xl hover:shadow-cyan-950/20 backdrop-blur-md overflow-hidden"
    >
      {/* Cover Artwork */}
      <div className="relative w-full aspect-video rounded-2xl overflow-hidden bg-zinc-800/80 mb-4">
        {item.poster_url && !imageError ? (
          <img
            src={item.poster_url}
            alt={item.title}
            onError={() => setImageError(true)}
            className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
            loading="lazy"
          />
        ) : (
          <div className="w-full h-full flex flex-col items-center justify-center text-zinc-600 gap-2">
            <Gamepad2 className="w-12 h-12" />
            <span className="text-xs">بدون تصویر</span>
          </div>
        )}

        {/* Source Badge */}
        <div className="absolute top-2.5 start-2.5 flex items-center gap-1 px-2.5 py-1 rounded-full bg-zinc-950/80 border border-zinc-800/80 text-2xs text-zinc-300 font-medium backdrop-blur-md">
          <span>{item.source_id}</span>
        </div>

        {/* Total Size Badge */}
        {primaryRelease?.total_size && (
          <div className="absolute top-2.5 end-2.5 flex items-center gap-1 px-2 py-0.5 rounded-full bg-zinc-950/80 border border-zinc-800/80 text-2xs font-mono text-zinc-300 backdrop-blur-md">
            <HardDrive className="w-3 h-3 text-cyan-400" />
            <TechnicalText>{primaryRelease.total_size}</TechnicalText>
          </div>
        )}
      </div>

      {/* Title & Metadata */}
      <div className="flex flex-col gap-1 mb-2">
        <h3 className="font-bold text-base text-zinc-100 line-clamp-1" title={item.title}>
          {item.title}
        </h3>

        {item.original_title && (
          <TechnicalText className="text-xs text-zinc-400 line-clamp-1">
            {item.original_title}
          </TechnicalText>
        )}
      </div>

      {/* Release Group & Version */}
      {primaryRelease && (
        <div className="flex items-center gap-2 flex-wrap text-2xs mb-2">
          {primaryRelease.release_group && (
            <span className="flex items-center gap-1 px-2 py-0.5 rounded-md bg-zinc-800 border border-zinc-700/60 text-zinc-300">
              <Tag className="w-3 h-3 text-cyan-400" />
              <TechnicalText>{primaryRelease.release_group}</TechnicalText>
            </span>
          )}

          {primaryRelease.version && (
            <span className="px-2 py-0.5 rounded-md bg-zinc-800/70 border border-zinc-700/40 text-zinc-400">
              <TechnicalText>{primaryRelease.version}</TechnicalText>
            </span>
          )}
        </div>
      )}

      {/* Description */}
      {item.description && (
        <p
          className="text-xs text-zinc-400 line-clamp-2 leading-relaxed mb-3"
          title={item.description}
        >
          {item.description}
        </p>
      )}

      {/* Password Pill */}
      {primaryRelease?.archive_password && (
        <div className="mb-3">
          <PasswordPill password={primaryRelease.archive_password} />
        </div>
      )}

      {/* Source page link */}
      <a
        href={item.page_url}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-1 text-2xs text-zinc-500 hover:text-cyan-400 transition-colors self-start mb-2"
      >
        <span>مشاهده در سایت مرجع</span>
        <ExternalLink className="w-3 h-3" />
      </a>

      {/* Parts List */}
      {primaryRelease && (
        <div className="mt-auto border-t border-zinc-800/80 pt-2 flex flex-col gap-4">
          <GamePartList
            parts={primaryRelease.parts}
            hasMissingParts={primaryRelease.has_missing_parts}
            missingPartNumbers={primaryRelease.missing_part_numbers}
            releaseId={primaryRelease.id}
          />

          {otherReleases.map((release, index) => (
            <div key={release.id} className="border-t border-zinc-800/60 pt-3">
              <div className="text-2xs text-zinc-500 mb-2">
                آرشیو {index + 2}
                {release.release_group && ` · ${release.release_group}`}
                {release.total_size && ` · ${release.total_size}`}
              </div>
              <GamePartList
                parts={release.parts}
                hasMissingParts={release.has_missing_parts}
                missingPartNumbers={release.missing_part_numbers}
                releaseId={release.id}
              />
            </div>
          ))}
        </div>
      )}
    </article>
  )
}
