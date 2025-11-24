import { SelectHTMLAttributes, forwardRef } from 'react';
import { ChevronDown } from 'lucide-react';

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

const Select = forwardRef<HTMLSelectElement, SelectProps>(
  (
    {
      label,
      error,
      helperText,
      className = '',
      children,
      ...props
    },
    ref
  ) => {
    const hasError = !!error;

    const baseStyles =
      'w-full px-4 py-2.5 bg-slate-700 border rounded-xl text-slate-100 transition-all duration-200 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed appearance-none cursor-pointer';

    const stateStyles = hasError
      ? 'border-red-500 focus:border-red-400 focus:ring-2 focus:ring-red-500/30'
      : 'border-slate-600 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30';

    return (
      <div className="w-full">
        {label && (
          <label className="block text-sm font-medium text-slate-300 mb-2">
            {label}
          </label>
        )}
        <div className="relative">
          <select
            ref={ref}
            className={`${baseStyles} ${stateStyles} ${className}`}
            {...props}
          >
            {children}
          </select>
          <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400">
            <ChevronDown size={18} />
          </div>
        </div>
        {(error || helperText) && (
          <p
            className={`mt-1.5 text-xs ${
              hasError ? 'text-red-400' : 'text-slate-400'
            }`}
          >
            {error || helperText}
          </p>
        )}
      </div>
    );
  }
);

Select.displayName = 'Select';

export default Select;
