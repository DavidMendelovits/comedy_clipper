import { useEffect } from 'react'
import { RouterProvider } from 'react-router-dom'
import { router } from './router'
import { setupJobEventListeners } from './stores/jobsStore'

function App() {
  // Set up job event listeners (only once on mount)
  useEffect(() => {
    if (!window.electron) {
      console.error('Electron API not available! Preload script may not have loaded.')
      return
    }

    console.log('Electron API available:', Object.keys(window.electron))

    // Initialize job event listeners
    setupJobEventListeners()
  }, [])

  return <RouterProvider router={router} />
}

export default App
