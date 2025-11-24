import React from 'react';
import { Video, GitCompare, FolderOutput } from 'lucide-react';

export type TabType = 'process' | 'compare' | 'results';

interface TabLayoutProps {
  activeTab: TabType;
  onTabChange: (tab: TabType) => void;
  children: React.ReactNode;
}

interface Tab {
  id: TabType;
  label: string;
  icon: React.ElementType;
}

const tabs: Tab[] = [
  { id: 'process', label: 'Process', icon: Video },
  { id: 'compare', label: 'Compare', icon: GitCompare },
  { id: 'results', label: 'Results', icon: FolderOutput },
];

export function TabLayout({ activeTab, onTabChange, children }: TabLayoutProps) {
  return (
    <div className="flex flex-col h-screen bg-[var(--color-bg-primary)]">
      {/* Header with macOS traffic light padding */}
      <header className="border-b border-[var(--color-border)] bg-[var(--color-bg-secondary)]">
        {/* Safe area for macOS traffic lights - hiddenInset style */}
        <div className="flex items-center justify-between px-6 py-4" style={{ paddingLeft: '88px' }}>
          <h1 className="text-2xl font-bold text-gradient">
            Comedy Clipper
          </h1>
        </div>
      </header>

      {/* Tabs */}
      <div className="border-b border-[var(--color-border)] bg-[var(--color-bg-secondary)]">
        {/* Tabs aligned with header, no extra left padding needed */}
        <nav className="flex" style={{ paddingLeft: '88px' }}>
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;

            return (
              <button
                key={tab.id}
                onClick={() => onTabChange(tab.id)}
                className={`
                  relative flex items-center gap-2 px-6 py-3 text-sm font-medium
                  transition-colors duration-200
                  ${isActive
                    ? 'text-[var(--color-primary)]'
                    : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
                  }
                `}
              >
                <Icon size={18} />
                <span>{tab.label}</span>

                {/* Active indicator */}
                {isActive && (
                  <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[var(--color-primary)]" />
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Content */}
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  );
}
