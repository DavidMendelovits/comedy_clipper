/**
 * App Layout
 * Main layout wrapper with navigation for all pages
 */

import { Outlet, NavLink } from 'react-router-dom';
import { Home, Video, GitCompare, History, Settings } from 'lucide-react';
import { useJobsStore } from '../../stores/jobsStore';

export function AppLayout() {
  const activeJobsCount = useJobsStore((state) => state.getActiveJobsCount());

  const navItems = [
    { to: '/', label: 'Dashboard', icon: Home },
    // { to: '/process', label: 'Process', icon: Video },
    { to: '/jobs', label: 'Jobs', icon: History },
    // { to: '/compare', label: 'Compare', icon: GitCompare },
    // { to: '/settings', label: 'Settings', icon: Settings },
  ];

  return (
    <div className="flex flex-col h-screen bg-[var(--color-bg-primary)]">
      {/* Background pattern */}
      <div className="absolute inset-0 opacity-5 pointer-events-none">
        <div
          className="absolute inset-0"
          style={{
            backgroundImage: `
              linear-gradient(to right, var(--color-border) 1px, transparent 1px),
              linear-gradient(to bottom, var(--color-border) 1px, transparent 1px)
            `,
            backgroundSize: '40px 40px',
          }}
        />
      </div>

      {/* Header with macOS traffic light padding */}
      <header className="relative z-10 border-b border-[var(--color-border)] bg-[var(--color-bg-secondary)]">
        <div className="flex items-center justify-between px-6 py-4" style={{ paddingLeft: '88px' }}>
          <h1 className="text-2xl font-bold text-gradient">
            Comedy Clipper
          </h1>
        </div>
      </header>

      {/* Navigation */}
      <nav className="relative z-10 border-b border-[var(--color-border)] bg-[var(--color-bg-secondary)]">
        <div className="flex" style={{ paddingLeft: '88px' }}>
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) => `
                  relative flex items-center gap-2 px-6 py-3 text-sm font-medium
                  transition-colors duration-200
                  ${isActive
                    ? 'text-[var(--color-primary)]'
                    : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
                  }
                `}
              >
                {({ isActive }) => (
                  <>
                    <Icon size={18} />
                    <span>{item.label}</span>
                    {item.to === '/jobs' && activeJobsCount > 0 && (
                      <span className="ml-1 px-1.5 py-0.5 text-xs font-semibold rounded-full bg-[var(--color-primary)] text-white">
                        {activeJobsCount}
                      </span>
                    )}
                    {isActive && (
                      <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[var(--color-primary)]" />
                    )}
                  </>
                )}
              </NavLink>
            );
          })}
        </div>
      </nav>

      {/* Main content */}
      <main className="relative z-10 flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
