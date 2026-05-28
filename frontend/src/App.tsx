import { useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import Shell from './components/Shell'
import { loadConfig } from './lib/appConfig'
import { ConfigContext } from './lib/ConfigContext'
import ApprovedRecordsPage from './pages/ApprovedRecords'
import ExplorerPage from './pages/Explorer'
import IngestionJobsPage from './pages/IngestionJobs'
import ReviewQueuePage from './pages/ReviewQueue'
import UploadCenter from './pages/UploadCenter'

export default function App() {
  const [config, setConfig] = useState(loadConfig)

  return (
    <ConfigContext.Provider value={{ config, setConfig }}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Shell />}>
            <Route index element={<Navigate to="/uploads" replace />} />
            <Route path="uploads" element={<UploadCenter />} />
            <Route path="jobs" element={<IngestionJobsPage />} />
            <Route path="review" element={<ReviewQueuePage />} />
            <Route path="approved" element={<ApprovedRecordsPage />} />
            <Route path="explorer" element={<ExplorerPage />} />
            <Route path="*" element={<Navigate to="/uploads" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ConfigContext.Provider>
  )
}
