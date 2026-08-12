import React, { Suspense } from 'react'
import { Routes, Route, useLocation, Navigate, Link } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import { Toaster } from 'sonner'
import { ProtectedRoute } from '@/components/common/ProtectedRoute'
import { SkeletonPulse } from '@/components/common/SkeletonPulse'
import LoginPage from '@/pages/LoginPage'
import RegisterPage from '@/pages/RegisterPage'
import WatchlistPage from '@/pages/WatchlistPage'
import { AppShell } from '@/components/layout/AppShell'
import TradingPage from '@/pages/TradingPage'
import StockDetailPage from '@/pages/StockDetailPage'
import StockSearchPage from '@/pages/StockSearchPage'
import AIResearchPage from '@/pages/AIResearchPage'
import BacktestPage from '@/pages/BacktestPage'
import ActivityPage from '@/pages/ActivityPage'
import AdminPage from '@/pages/AdminPage'
import AutoTradePage from '@/pages/AutoTradePage'
import DashboardPage from '@/pages/DashboardPage'
import PortfolioPage from '@/pages/PortfolioPage'
import { useAuthStore } from '@/store/authStore'

// Lazy-loaded pages
const DailyBriefPage = React.lazy(() => import('@/pages/DailyBriefPage'))
const PennyStocksPage = React.lazy(() => import('@/pages/PennyStocksPage'))
const NewsFeedPage = React.lazy(() => import('@/pages/NewsFeedPage'))
const PredictionsPage = React.lazy(() => import('@/pages/PredictionsPage'))
const AlertsPage = React.lazy(() => import('@/pages/AlertsPage'))
const SettingsPage = React.lazy(() => import('@/pages/SettingsPage'))

/** Full-page loading fallback used by Suspense */
function FullPageSpinner() {
  return (
    <div className="flex flex-col gap-4 p-8 w-full h-screen">
      <SkeletonPulse className="h-10 w-48" />
      <SkeletonPulse className="h-6 w-full" />
      <SkeletonPulse className="h-6 w-5/6" />
      <SkeletonPulse className="h-6 w-4/6" />
      <div className="flex gap-4 mt-4">
        <SkeletonPulse className="h-40 flex-1" />
        <SkeletonPulse className="h-40 flex-1" />
        <SkeletonPulse className="h-40 flex-1" />
      </div>
    </div>
  )
}

/** 404 page shown for unknown routes */
function NotFoundPage() {
  return (
    <div className="flex flex-col items-center justify-center h-screen gap-6 text-white">
      <h1 className="text-6xl font-bold text-[#6366f1]">404</h1>
      <p className="text-xl text-[#94a3b8]">Page not found</p>
      <Link
        to="/dashboard"
        className="px-6 py-2 rounded-lg bg-[#6366f1] hover:bg-[#4f46e5] transition-colors text-white font-medium"
      >
        Go to Dashboard
      </Link>
    </div>
  )
}

/** Root redirect: authenticated → /market, unauthenticated → /login */
function RootRedirect() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  return isAuthenticated ? <Navigate to="/market" replace /> : <Navigate to="/login" replace />
}

export default function App() {
  const location = useLocation()

  return (
    <AnimatePresence mode="wait">
      <Toaster
        position="top-right"
        theme="dark"
        richColors
        closeButton
      />
      <Routes location={location} key={location.pathname}>
        {/* Public routes */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        {/* Root redirect */}
        <Route path="/" element={<RootRedirect />} />

        {/* Protected routes — wrapped with AppShell */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <AppShell>
                <DashboardPage />
              </AppShell>
            </ProtectedRoute>
          }
        />
        <Route
          path="/portfolio"
          element={
            <ProtectedRoute>
              <AppShell>
                <PortfolioPage />
              </AppShell>
            </ProtectedRoute>
          }
        />
        <Route
          path="/watchlist"
          element={
            <ProtectedRoute>
              <AppShell>
                <WatchlistPage />
              </AppShell>
            </ProtectedRoute>
          }
        />
        <Route
          path="/trading"
          element={
            <ProtectedRoute>
              <AppShell>
                <TradingPage />
              </AppShell>
            </ProtectedRoute>
          }
        />
        <Route
          path="/ai-research"
          element={
            <ProtectedRoute>
              <AppShell>
                <AIResearchPage />
              </AppShell>
            </ProtectedRoute>
          }
        />
        <Route
          path="/backtest"
          element={
            <ProtectedRoute>
              <AppShell>
                <BacktestPage />
              </AppShell>
            </ProtectedRoute>
          }
        />
        <Route
          path="/autotrade"
          element={
            <ProtectedRoute>
              <AppShell>
                <AutoTradePage />
              </AppShell>
            </ProtectedRoute>
          }
        />
        <Route
          path="/activity"
          element={
            <ProtectedRoute>
              <AppShell>
                <ActivityPage />
              </AppShell>
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin"
          element={
            <ProtectedRoute>
              <AppShell>
                <AdminPage />
              </AppShell>
            </ProtectedRoute>
          }
        />
        <Route
          path="/stock/search"
          element={
            <ProtectedRoute>
              <AppShell>
                <StockSearchPage />
              </AppShell>
            </ProtectedRoute>
          }
        />
        <Route
          path="/stock/:ticker"
          element={
            <ProtectedRoute>
              <AppShell>
                <StockDetailPage />
              </AppShell>
            </ProtectedRoute>
          }
        />

        {/* Lazy-loaded protected routes */}
        <Route
          path="/market"
          element={
            <ProtectedRoute>
              <AppShell>
                <Suspense fallback={<FullPageSpinner />}>
                  <DailyBriefPage />
                </Suspense>
              </AppShell>
            </ProtectedRoute>
          }
        />
        <Route
          path="/penny-stocks"
          element={
            <ProtectedRoute>
              <AppShell>
                <Suspense fallback={<FullPageSpinner />}>
                  <PennyStocksPage />
                </Suspense>
              </AppShell>
            </ProtectedRoute>
          }
        />
        <Route
          path="/news"
          element={
            <ProtectedRoute>
              <AppShell>
                <Suspense fallback={<FullPageSpinner />}>
                  <NewsFeedPage />
                </Suspense>
              </AppShell>
            </ProtectedRoute>
          }
        />
        <Route
          path="/predictions"
          element={
            <ProtectedRoute>
              <AppShell>
                <Suspense fallback={<FullPageSpinner />}>
                  <PredictionsPage />
                </Suspense>
              </AppShell>
            </ProtectedRoute>
          }
        />
        <Route
          path="/alerts"
          element={
            <ProtectedRoute>
              <AppShell>
                <Suspense fallback={<FullPageSpinner />}>
                  <AlertsPage />
                </Suspense>
              </AppShell>
            </ProtectedRoute>
          }
        />
        <Route
          path="/settings"
          element={
            <ProtectedRoute>
              <AppShell>
                <Suspense fallback={<FullPageSpinner />}>
                  <SettingsPage />
                </Suspense>
              </AppShell>
            </ProtectedRoute>
          }
        />

        {/* Catch-all 404 */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </AnimatePresence>
  )
}
