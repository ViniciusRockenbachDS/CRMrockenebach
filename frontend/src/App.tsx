import { Navigate, Route, Routes } from 'react-router-dom'

import { AppLayout } from '@/components/layout/AppLayout'
import { ProtectedRoute } from '@/components/layout/ProtectedRoute'
import ClientDetailPage from '@/pages/ClientDetailPage'
import ClientsPage from '@/pages/ClientsPage'
import DashboardPage from '@/pages/DashboardPage'
import LoginPage from '@/pages/LoginPage'
import PaymentsPage from '@/pages/PaymentsPage'
import PipelinePage from '@/pages/PipelinePage'
import UsersPage from '@/pages/UsersPage'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="clientes" element={<ClientsPage />} />
          <Route path="clientes/:id" element={<ClientDetailPage />} />
          <Route path="funil" element={<PipelinePage />} />
          <Route path="pagamentos" element={<PaymentsPage />} />
          <Route element={<ProtectedRoute adminOnly />}>
            <Route path="usuarios" element={<UsersPage />} />
          </Route>
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
