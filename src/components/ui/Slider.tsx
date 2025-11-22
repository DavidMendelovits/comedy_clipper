import React, { InputHTMLAttributes, forwardRef, useState } from 'react';

export interface SliderProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: string;
  showValue?: boolean;
  valueFormatter?: (value: number) => string;
  unit?: string;
}

const Slider = forwardRef<HTMLInputElement, SliderProps>(
  (
    {
      label,
      showValue = true,
      valueFormatter,
      unit = '',
      min = 0,
      max = 100,
      step = 1,
      value,
      defaultValue,
      onChange,
      className = '',
      ...props
    },
    ref
  ) => {
    const [internalValue, setInternalValue] = useState(
      (value as number) || (defaultValue as number) || (min as number)
    );

    const currentValue = value !== undefined ? (value as number) : internalValue;

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      const newValue = parseFloat(e.target.value);
      setInternalValue(newValue);
      onChange?.(e);
    };

    const percentage = ((currentValue - (min as number)) / ((max as number) - (min as number))) * 100;

    const displayValue = valueFormatter
      ? valueFormatter(currentValue)
      : `${currentValue}${unit}`;

    return (
      <div className={`w-full ${className}`}>
        {(label || showValue) && (
          <div className="flex items-center justify-between mb-2">
            {label && (
              <label className="text-sm font-medium text-slate-300">
                {label}
              </label>
            )}
            {showValue && (
              <span className="text-sm font-mono text-primary-400 bg-slate-800 px-2 py-0.5 rounded">
                {displayValue}
              </span>
            )}
          </div>
        )}
        <div className="relative">
          <input
            ref={ref}
            type="range"
            min={min}
            max={max}
            step={step}
            value={currentValue}
            onChange={handleChange}
            className="slider-input w-full"
            {...props}
          />
          <style>{`
            .slider-input {
              -webkit-appearance: none;
              appearance: none;
              height: 6px;
              border-radius: 9999px;
              background: linear-gradient(
                to right,
                rgb(14, 165, 233) 0%,
                rgb(56, 189, 248) ${percentage}%,
                rgb(71, 85, 105) ${percentage}%,
                rgb(71, 85, 105) 100%
              );
              outline: none;
              transition: all 0.2s ease;
            }

            .slider-input:hover {
              background: linear-gradient(
                to right,
                rgb(14, 165, 233) 0%,
                rgb(56, 189, 248) ${percentage}%,
                rgb(100, 116, 139) ${percentage}%,
                rgb(100, 116, 139) 100%
              );
            }

            .slider-input::-webkit-slider-thumb {
              -webkit-appearance: none;
              appearance: none;
              width: 18px;
              height: 18px;
              border-radius: 50%;
              background: linear-gradient(135deg, rgb(14, 165, 233), rgb(56, 189, 248));
              cursor: pointer;
              box-shadow: 0 2px 8px rgba(14, 165, 233, 0.4);
              transition: all 0.2s ease;
            }

            .slider-input::-webkit-slider-thumb:hover {
              transform: scale(1.1);
              box-shadow: 0 4px 12px rgba(14, 165, 233, 0.6);
            }

            .slider-input::-webkit-slider-thumb:active {
              transform: scale(1.05);
            }

            .slider-input::-moz-range-thumb {
              width: 18px;
              height: 18px;
              border: none;
              border-radius: 50%;
              background: linear-gradient(135deg, rgb(14, 165, 233), rgb(56, 189, 248));
              cursor: pointer;
              box-shadow: 0 2px 8px rgba(14, 165, 233, 0.4);
              transition: all 0.2s ease;
            }

            .slider-input::-moz-range-thumb:hover {
              transform: scale(1.1);
              box-shadow: 0 4px 12px rgba(14, 165, 233, 0.6);
            }

            .slider-input::-moz-range-thumb:active {
              transform: scale(1.05);
            }

            .slider-input:focus {
              outline: none;
            }

            .slider-input:focus::-webkit-slider-thumb {
              box-shadow: 0 0 0 4px rgba(14, 165, 233, 0.2);
            }

            .slider-input:focus::-moz-range-thumb {
              box-shadow: 0 0 0 4px rgba(14, 165, 233, 0.2);
            }

            .slider-input:disabled {
              opacity: 0.5;
              cursor: not-allowed;
            }

            .slider-input:disabled::-webkit-slider-thumb {
              cursor: not-allowed;
            }

            .slider-input:disabled::-moz-range-thumb {
              cursor: not-allowed;
            }
          `}</style>
        </div>
      </div>
    );
  }
);

Slider.displayName = 'Slider';

export default Slider;
