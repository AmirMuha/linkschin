import React from 'react'

interface TechnicalTextProps {
  children: React.ReactNode
  className?: string
  as?: 'span' | 'code' | 'div'
}

/**
 * Enforces strict Left-to-Right (LTR) isolation for technical strings
 * (filenames, codecs, part labels, hashes, URLs, passwords)
 * to prevent punctuation and extension inversion inside Persian RTL layouts.
 */
export function TechnicalText({
  children,
  className = '',
  as: Component = 'span',
}: TechnicalTextProps) {
  return (
    <Component
      dir="ltr"
      style={{ unicodeBidi: 'isolate' }}
      className={`font-mono inline-block text-left ${className}`}
    >
      {children}
    </Component>
  )
}
