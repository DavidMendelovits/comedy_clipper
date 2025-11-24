/**
 * React Router Configuration
 */

import { createHashRouter } from 'react-router-dom';
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
    element: <AppLayout />,
    children: [
      {
        index: true,
        element: <DashboardPage />,
      },
      {
        path: 'process',
        element: <ProcessPage />,
      },
      {
        path: 'jobs',
        element: <JobHistoryPage />,
      },
      {
        path: 'jobs/:jobId',
        element: <JobDetailPage />,
      },
      {
        path: 'compare',
        element: <ComparePage />,
      },
      {
        path: 'settings',
        element: <SettingsPage />,
      },
    ],
  },
]);
