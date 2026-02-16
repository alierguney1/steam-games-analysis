import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Dashboard from './pages/Dashboard'
import Games from './pages/Games'
import GameDetail from './pages/GameDetail'
import CausalAnalysis from './pages/CausalAnalysis'
import SurvivalAnalysis from './pages/SurvivalAnalysis'
import DataStatus from './pages/DataStatus'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/games" element={<Games />} />
          <Route path="/games/:id" element={<GameDetail />} />
          <Route path="/causal-analysis" element={<CausalAnalysis />} />
          <Route path="/survival-analysis" element={<SurvivalAnalysis />} />
          <Route path="/data-status" element={<DataStatus />} />
        </Routes>
      </Router>
    </QueryClientProvider>
  )
}

export default App
