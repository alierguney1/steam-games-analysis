import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

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
        <div className="min-h-screen bg-gray-50">
          <Routes>
            <Route path="/" element={
              <div className="flex items-center justify-center h-screen">
                <div className="text-center">
                  <h1 className="text-4xl font-bold text-gray-900 mb-4">
                    Steam Games Analysis
                  </h1>
                  <p className="text-xl text-gray-600 mb-8">
                    Player Retention and Causal Pricing Analysis Platform
                  </p>
                  <div className="space-y-2 text-left max-w-md mx-auto">
                    <p className="text-gray-700">✅ Difference-in-Differences (DiD) Model</p>
                    <p className="text-gray-700">✅ Kaplan-Meier Survival Analysis</p>
                    <p className="text-gray-700">✅ Cox Proportional Hazards Model</p>
                    <p className="text-gray-700">✅ Price Elasticity Calculator</p>
                    <p className="text-gray-700">✅ Real-time Data Pipeline</p>
                  </div>
                  <div className="mt-8 text-sm text-gray-500">
                    Backend API: <a href="/api/docs" className="text-blue-600 hover:underline">/api/docs</a>
                  </div>
                </div>
              </div>
            } />
          </Routes>
        </div>
      </Router>
    </QueryClientProvider>
  )
}

export default App
