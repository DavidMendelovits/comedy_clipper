/**
 * React Router Configuration - Simplified for Pose Detection
 */

import { createHashRouter } from 'react-router-dom'
import { AppLayout } from './components/layout/AppLayout'
import { UploadPage } from './pages/UploadPage'
import { JobDetailPage } from './pages/JobDetailPage'
import { JobHistoryPage } from './pages/JobHistoryPage'

export const router = createHashRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      {
        index: true,
        element: <UploadPage />,
      },
      {
        path: 'jobs',
        element: <JobHistoryPage />,
      },
      {
        path: 'jobs/:jobId',
        element: <JobDetailPage />,
      },
    ],
  },
])
