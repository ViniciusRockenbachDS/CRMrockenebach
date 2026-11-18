import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { LoadingState } from '@/components/ui'
import { useAuth } from '@/contexts/AuthContext'

export function ProtectedRoute({ adminOnly = false }: { adminOnly?: boolean }) {
  const { user, loading, isAdmin } = useAuth()
  const location = useLocation()

  if (loading) return <LoadingState label="Verificando sessão..." />
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  if (adminOnly && !isAdmin) return <Navigate to="/" replace />
  return <Outlet />
}
