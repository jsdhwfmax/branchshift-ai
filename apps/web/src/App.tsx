import { Navigate, Route, Routes } from 'react-router-dom'
import HomePage from './routes/HomePage'
import RunPage from './routes/RunPage'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/runs/:runId" element={<RunPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

