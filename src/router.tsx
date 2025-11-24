/**
 * React Router Configuration
 */

import { createHashRouter } from 'react-router-dom';
import { ErrorBoundary } from './components/ErrorBoundary';
import { AppLayout } from './components/layout/AppLayout';
import { DashboardPage } from './pages/DashboardPage';
import { ProcessPage } from './pages/ProcessPage';
import { JobHistoryPage } from './pages/JobHistoryPage';
import { JobDetailPage } from './pages/JobDetailPage';
import { ComparePage } from './pages/ComparePage';
import { SettingsPage } from './pages/SettingsPage';

export const router = createHashRouter([
  {
    path: '/',
    element: (
      <ErrorBoundary>
        <AppLayout />
      </ErrorBoundary>
    ),
    children: [
      {
        index: true,
        element: (
          <ErrorBoundary>
            <DashboardPage />
          </ErrorBoundary>
        ),
      },
      {
        path: 'process',
        element: (
          <ErrorBoundary>
            <ProcessPage />
          </ErrorBoundary>
        ),
      },
      {
        path: 'jobs',
        element: (
          <ErrorBoundary>
            <JobHistoryPage />
          </ErrorBoundary>
        ),
      },
      {
        path: 'jobs/:jobId',
        element: (
          <ErrorBoundary>
            <JobDetailPage />
          </ErrorBoundary>
        ),
      },
      {
        path: 'compare',
        element: (
          <ErrorBoundary>
            <ComparePage />
          </ErrorBoundary>
        ),
      },
      {
        path: 'settings',
        element: (
          <ErrorBoundary>
            <SettingsPage />
          </ErrorBoundary>
        ),
      },
    ],
  },
]);
