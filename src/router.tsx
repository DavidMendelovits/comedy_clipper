/**
 * React Router Configuration - Simplified for Pose Detection
 */

import { createHashRouter } from 'react-router-dom'
import { UploadPage } from './pages/UploadPage'
import { JobDetailPage } from './pages/JobDetailPage'

export const router = createHashRouter([
  {
    path: '/',
    element: <UploadPage />,
  },
  {
    path: '/jobs/:jobId',
    element: <JobDetailPage />,
  },
])
