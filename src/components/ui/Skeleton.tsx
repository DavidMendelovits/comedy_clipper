import React, { HTMLAttributes } from 'react';

export interface SkeletonProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'text' | 'circular' | 'rectangular';
  width?: string | number;
  height?: string | number;
  count?: number;
}

const Skeleton: React.FC<SkeletonProps> = ({
  variant = 'text',
  width,
  height,
  count = 1,
  className = '',
  ...props
}) => {
  const baseStyles = 'shimmer bg-slate-700/50';

  const variantStyles = {
    text: 'rounded h-4',
    circular: 'rounded-full',
    rectangular: 'rounded-lg',
  };

  const style: React.CSSProperties = {
    width: width || (variant === 'text' ? '100%' : variant === 'circular' ? '40px' : '100%'),
    height: height || (variant === 'text' ? undefined : variant === 'circular' ? '40px' : '100px'),
  };

  if (count === 1) {
    return (
      <div
        className={`${baseStyles} ${variantStyles[variant]} ${className}`}
        style={style}
        {...props}
      />
    );
  }

  return (
    <div className="space-y-2">
      {Array.from({ length: count }).map((_, index) => (
        <div
          key={index}
          className={`${baseStyles} ${variantStyles[variant]} ${className}`}
          style={style}
          {...props}
        />
      ))}
    </div>
  );
};

// Pre-made skeleton patterns for common use cases
export const SkeletonCard: React.FC<{ className?: string }> = ({ className = '' }) => (
  <div className={`p-6 bg-slate-800 rounded-xl border border-slate-700/50 ${className}`}>
    <div className="flex items-center gap-4 mb-4">
      <Skeleton variant="circular" width={48} height={48} />
      <div className="flex-1 space-y-2">
        <Skeleton variant="text" width="60%" />
        <Skeleton variant="text" width="40%" />
      </div>
    </div>
    <Skeleton variant="rectangular" height={120} className="mb-3" />
    <Skeleton variant="text" count={3} />
  </div>
);

export const SkeletonList: React.FC<{ count?: number; className?: string }> = ({
  count = 5,
  className = '',
}) => (
  <div className={`space-y-3 ${className}`}>
    {Array.from({ length: count }).map((_, index) => (
      <div
        key={index}
        className="flex items-center gap-3 p-3 bg-slate-800 rounded-lg border border-slate-700/50"
      >
        <Skeleton variant="circular" width={40} height={40} />
        <div className="flex-1 space-y-2">
          <Skeleton variant="text" width="70%" />
          <Skeleton variant="text" width="40%" />
        </div>
      </div>
    ))}
  </div>
);

export const SkeletonTable: React.FC<{ rows?: number; columns?: number; className?: string }> = ({
  rows = 5,
  columns = 4,
  className = '',
}) => (
  <div className={`overflow-hidden rounded-xl border border-slate-700/50 ${className}`}>
    <div className="bg-slate-800 p-4 border-b border-slate-700/50">
      <div className="flex gap-4">
        {Array.from({ length: columns }).map((_, index) => (
          <Skeleton key={index} variant="text" width="20%" />
        ))}
      </div>
    </div>
    <div className="divide-y divide-slate-700/50">
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={rowIndex} className="bg-slate-800 p-4">
          <div className="flex gap-4">
            {Array.from({ length: columns }).map((_, colIndex) => (
              <Skeleton key={colIndex} variant="text" width="20%" />
            ))}
          </div>
        </div>
      ))}
    </div>
  </div>
);

export default Skeleton;
