/**
 * RatingIndicator Component
 *
 * Displays a 1-5 rating as colored dots.
 * Used for showing speed/quality ratings in preset selectors.
 */

import React from 'react'

interface RatingIndicatorProps {
  rating: number  // 1-5
  maxRating?: number  // Default: 5
  activeColor?: string
  inactiveColor?: string
}

export function RatingIndicator({
  rating,
  maxRating = 5,
  activeColor = 'var(--color-primary)',
  inactiveColor = 'var(--color-border)'
}: RatingIndicatorProps) {
  const clampedRating = Math.max(0, Math.min(rating, maxRating))

  return (
    <div className="flex items-center gap-1">
      {Array.from({ length: maxRating }, (_, i) => {
        const isActive = i < clampedRating
        return (
          <div
            key={i}
            className="w-1.5 h-1.5 rounded-full transition-colors"
            style={{
              backgroundColor: isActive ? activeColor : inactiveColor
            }}
          />
        )
      })}
    </div>
  )
}
