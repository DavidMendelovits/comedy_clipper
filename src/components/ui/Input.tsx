import React, { InputHTMLAttributes, forwardRef, useState } from 'react';
import { CheckCircle2, XCircle, AlertCircle } from 'lucide-react';

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  success?: boolean;
  helperText?: string;
  icon?: React.ReactNode;
  iconPosition?: 'left' | 'right';
  floatingLabel?: boolean;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  (
    {
      label,
      error,
      success = false,
      helperText,
      icon,
      iconPosition = 'left',
      floatingLabel = false,
      className = '',
      type = 'text',
      ...props
    },
    ref
  ) => {
    const [isFocused, setIsFocused] = useState(false);
    const [hasValue, setHasValue] = useState(!!props.value || !!props.defaultValue);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      setHasValue(e.target.value.length > 0);
      props.onChange?.(e);
    };

    const hasError = !!error;
    const hasSuccess = success && !hasError;

    const baseStyles =
      'w-full px-4 py-2.5 bg-slate-700 border rounded-xl text-slate-100 placeholder-slate-400 transition-all duration-200 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed';

    const stateStyles = hasError
      ? 'border-red-500 focus:border-red-400 focus:ring-2 focus:ring-red-500/30'
      : hasSuccess
      ? 'border-emerald-500 focus:border-emerald-400 focus:ring-2 focus:ring-emerald-500/30'
      : 'border-slate-600 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30';

    const iconPaddingClass =
      icon && iconPosition === 'left' ? 'pl-10' : icon && iconPosition === 'right' ? 'pr-10' : '';

    const StatusIcon = hasError
      ? XCircle
      : hasSuccess
      ? CheckCircle2
      : helperText
      ? AlertCircle
      : null;

    if (floatingLabel && label) {
      return (
        <div className="relative">
          <input
            ref={ref}
            type={type}
            className={`${baseStyles} ${stateStyles} ${iconPaddingClass} ${className} peer`}
            placeholder=" "
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            onChange={handleChange}
            {...props}
          />
          <label
            className={`absolute left-4 transition-all duration-200 pointer-events-none
              ${
                isFocused || hasValue
                  ? '-top-2 text-xs bg-slate-700 px-2 text-primary-400'
                  : 'top-2.5 text-sm text-slate-400'
              }
            `}
          >
            {label}
          </label>
          {icon && iconPosition === 'left' && (
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">
              {icon}
            </div>
          )}
          {icon && iconPosition === 'right' && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400">
              {icon}
            </div>
          )}
          {StatusIcon && (
            <div
              className={`absolute right-3 top-1/2 -translate-y-1/2 ${
                hasError ? 'text-red-400' : hasSuccess ? 'text-emerald-400' : 'text-slate-400'
              }`}
            >
              <StatusIcon size={18} />
            </div>
          )}
          {(error || helperText) && (
            <p
              className={`mt-1.5 text-xs ${
                hasError ? 'text-red-400' : hasSuccess ? 'text-emerald-400' : 'text-slate-400'
              }`}
            >
              {error || helperText}
            </p>
          )}
        </div>
      );
    }

    return (
      <div className="w-full">
        {label && (
          <label className="block text-sm font-medium text-slate-300 mb-2">
            {label}
          </label>
        )}
        <div className="relative">
          <input
            ref={ref}
            type={type}
            className={`${baseStyles} ${stateStyles} ${iconPaddingClass} ${className}`}
            onChange={handleChange}
            {...props}
          />
          {icon && iconPosition === 'left' && (
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">
              {icon}
            </div>
          )}
          {icon && iconPosition === 'right' && !StatusIcon && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400">
              {icon}
            </div>
          )}
          {StatusIcon && (
            <div
              className={`absolute right-3 top-1/2 -translate-y-1/2 ${
                hasError ? 'text-red-400' : hasSuccess ? 'text-emerald-400' : 'text-slate-400'
              }`}
            >
              <StatusIcon size={18} />
            </div>
          )}
        </div>
        {(error || helperText) && (
          <p
            className={`mt-1.5 text-xs ${
              hasError ? 'text-red-400' : hasSuccess ? 'text-emerald-400' : 'text-slate-400'
            }`}
          >
            {error || helperText}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

export default Input;
