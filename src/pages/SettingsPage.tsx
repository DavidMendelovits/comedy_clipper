/**
 * Settings Page
 * Application settings and configuration
 */

import { useState, useEffect } from 'react';
import { useSettingsStore } from '../stores';
import { Trash2, Database, RefreshCw } from 'lucide-react';

export function SettingsPage() {
  const config = useSettingsStore((state) => state.config);
  const setConfig = useSettingsStore((state) => state.setConfig);

  // Cache management state
  const [cacheStats, setCacheStats] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [clearing, setClearing] = useState(false);

  const loadCacheStats = async () => {
    setLoading(true);
    try {
      const stats = await window.electron?.getCacheStats();
      setCacheStats(stats);
    } catch (error) {
      console.error('Failed to load cache stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleClearCache = async () => {
    if (!confirm('Are you sure you want to clear all cached detection data? This cannot be undone.')) {
      return;
    }

    setClearing(true);
    try {
      await window.electron?.clearCache();
      await loadCacheStats(); // Reload stats
    } catch (error) {
      console.error('Failed to clear cache:', error);
      alert('Failed to clear cache');
    } finally {
      setClearing(false);
    }
  };

  useEffect(() => {
    loadCacheStats();
  }, []);

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

        {/* Cache Management */}
        <div className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg p-6 space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-xl font-semibold text-[var(--color-text-primary)] flex items-center gap-2">
                <Database size={24} />
                Detection Cache
              </h3>
              <p className="text-[var(--color-text-muted)] text-sm mt-1">
                Cached pose and face detection data for faster parameter tuning
              </p>
            </div>
            <button
              onClick={loadCacheStats}
              disabled={loading}
              className="flex items-center gap-2 px-3 py-2 bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-bg-hover)] border border-[var(--color-border)] text-[var(--color-text-primary)] rounded-lg transition-colors disabled:opacity-50"
            >
              <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
              Refresh
            </button>
          </div>

          {cacheStats ? (
            <>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg p-4">
                  <p className="text-[var(--color-text-muted)] text-sm mb-1">Cached Videos</p>
                  <p className="text-2xl font-bold text-[var(--color-text-primary)]">
                    {cacheStats.entry_count || 0}
                  </p>
                </div>
                <div className="bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg p-4">
                  <p className="text-[var(--color-text-muted)] text-sm mb-1">Total Size</p>
                  <p className="text-2xl font-bold text-[var(--color-text-primary)]">
                    {cacheStats.total_size_mb ? `${cacheStats.total_size_mb} MB` : '0 MB'}
                  </p>
                </div>
                <div className="bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg p-4">
                  <p className="text-[var(--color-text-muted)] text-sm mb-1">Cache Location</p>
                  <p className="text-sm font-mono text-[var(--color-text-primary)] truncate" title={cacheStats.cache_dir}>
                    {cacheStats.cache_dir || 'N/A'}
                  </p>
                </div>
              </div>

              {cacheStats.entry_count > 0 && (
                <div className="pt-4 border-t border-[var(--color-border)]">
                  <button
                    onClick={handleClearCache}
                    disabled={clearing}
                    className="flex items-center gap-2 px-4 py-2 bg-[var(--color-error)] hover:bg-red-600 text-white rounded-lg transition-colors disabled:opacity-50"
                  >
                    <Trash2 size={18} />
                    {clearing ? 'Clearing...' : 'Clear All Cache'}
                  </button>
                  <p className="text-xs text-[var(--color-text-muted)] mt-2">
                    This will remove all cached detection data. Videos will need to be reprocessed on next run.
                  </p>
                </div>
              )}
            </>
          ) : (
            <div className="text-center py-8 text-[var(--color-text-muted)]">
              {loading ? 'Loading cache stats...' : 'No cache data available'}
            </div>
          )}
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
