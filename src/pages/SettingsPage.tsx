/**
 * Settings Page
 * Application settings and configuration
 */

import React from 'react';
import { useSettingsStore } from '../stores';

export function SettingsPage() {
  const config = useSettingsStore((state) => state.config);
  const setConfig = useSettingsStore((state) => state.setConfig);

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-4xl mx-auto p-8 space-y-8">
        {/* Header */}
        <div>
          <h2 className="text-3xl font-bold text-[var(--color-text-primary)]">
            Settings
          </h2>
          <p className="text-[var(--color-text-muted)] mt-2">
            Configure your processing preferences
          </p>
        </div>

        {/* Processing Settings */}
        <div className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg p-6 space-y-6">
          <h3 className="text-xl font-semibold text-[var(--color-text-primary)]">
            Processing Settings
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
                Minimum Duration (seconds)
              </label>
              <input
                type="number"
                value={config.minDuration}
                onChange={(e) => setConfig({ minDuration: parseInt(e.target.value) || 3 })}
                className="w-full px-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-primary)]"
              />
              <p className="text-xs text-[var(--color-text-muted)] mt-1">
                Minimum clip length to keep
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
                Maximum Duration (seconds)
              </label>
              <input
                type="number"
                value={config.maxDuration || 30}
                onChange={(e) => setConfig({ maxDuration: parseInt(e.target.value) || 30 })}
                className="w-full px-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-primary)]"
              />
              <p className="text-xs text-[var(--color-text-muted)] mt-1">
                Maximum clip length to keep
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
                Output Directory
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={config.outputDir || ''}
                  onChange={(e) => setConfig({ outputDir: e.target.value })}
                  placeholder="Default output directory"
                  className="flex-1 px-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-primary)]"
                />
                <button
                  onClick={async () => {
                    const dir = await window.electron?.selectOutputDirectory();
                    if (dir) setConfig({ outputDir: dir });
                  }}
                  className="px-4 py-2 bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white rounded-lg transition-colors"
                >
                  Browse
                </button>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="debug"
                checked={config.debug || false}
                onChange={(e) => setConfig({ debug: e.target.checked })}
                className="w-4 h-4 text-[var(--color-primary)] bg-[var(--color-bg-tertiary)] border-[var(--color-border)] rounded focus:ring-[var(--color-primary)]"
              />
              <label htmlFor="debug" className="text-sm font-medium text-[var(--color-text-secondary)]">
                Enable debug mode (save debug frames)
              </label>
            </div>
          </div>
        </div>

        {/* About */}
        <div className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg p-6">
          <h3 className="text-xl font-semibold text-[var(--color-text-primary)] mb-4">
            About
          </h3>
          <p className="text-[var(--color-text-secondary)]">
            Comedy Clipper - AI-powered video processing for comedy content
          </p>
          <p className="text-[var(--color-text-muted)] text-sm mt-2">
            Version 1.0.0
          </p>
        </div>
      </div>
    </div>
  );
}
