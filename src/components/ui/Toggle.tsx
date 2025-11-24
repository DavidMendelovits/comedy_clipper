import { forwardRef, InputHTMLAttributes } from 'react';

export interface ToggleProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type' | 'size'> {
  label?: string;
  description?: string;
  size?: 'sm' | 'md' | 'lg';
}

const Toggle = forwardRef<HTMLInputElement, ToggleProps>(
  (
    {
      label,
      description,
      size = 'md',
      checked,
      disabled,
      className = '',
      ...props
    },
    ref
  ) => {
    const sizes = {
      sm: {
        track: 'w-8 h-4',
        thumb: 'w-3 h-3',
        translate: 'translate-x-4',
      },
      md: {
        track: 'w-11 h-6',
        thumb: 'w-5 h-5',
        translate: 'translate-x-5',
      },
      lg: {
        track: 'w-14 h-7',
        thumb: 'w-6 h-6',
        translate: 'translate-x-7',
      },
    };

    const currentSize = sizes[size];

    return (
      <label
        className={`flex items-start gap-3 cursor-pointer ${
          disabled ? 'opacity-50 cursor-not-allowed' : ''
        } ${className}`}
      >
        <div className="relative inline-block flex-shrink-0">
          <input
            ref={ref}
            type="checkbox"
            className="sr-only peer"
            checked={checked}
            disabled={disabled}
            {...props}
          />
          <div
            className={`${currentSize.track} rounded-full transition-all duration-300 ease-in-out
              ${
                checked
                  ? 'bg-gradient-to-r from-primary-600 to-primary-500 shadow-lg shadow-primary-500/30'
                  : 'bg-slate-700'
              }
              ${!disabled && 'peer-focus:ring-2 peer-focus:ring-primary-500/30 peer-focus:ring-offset-2 peer-focus:ring-offset-slate-900'}
            `}
          />
          <div
            className={`${currentSize.thumb} absolute top-0.5 left-0.5 rounded-full transition-all duration-300 ease-in-out transform
              ${checked ? `${currentSize.translate} bg-white shadow-md` : 'bg-slate-400 shadow-sm'}
            `}
          />
        </div>
        {(label || description) && (
          <div className="flex flex-col">
            {label && (
              <span className="text-sm font-medium text-slate-200">
                {label}
              </span>
            )}
            {description && (
              <span className="text-xs text-slate-400 mt-0.5">
                {description}
              </span>
            )}
          </div>
        )}
      </label>
    );
  }
);

Toggle.displayName = 'Toggle';

export default Toggle;
