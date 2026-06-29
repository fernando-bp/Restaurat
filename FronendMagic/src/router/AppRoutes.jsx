import { Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from '../features/auth/pages/LoginPage'
import MesasPage from '../features/mesas/pages/MesasPage'
import OrdenPage from '../features/ordenes/pages/OrdenPage'
import CocinaPage from '../features/cocina/pages/CocinaPage'
import CajaPage from '../features/caja/pages/CajaPage'
import CierreCajaPage from '../features/caja/pages/CierreCajaPage'
import RecetarioPage from '../features/recetario/pages/RecetarioPage'
import InventarioPage from '../features/inventario/pages/InventarioPage'
import BoldTestPage from '../features/boldTest/pages/BoldTestPage'
import FinanzasPage from '../features/finanzas/pages/FinanzasPage'
import PrivateRoute from './PrivateRoute'

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route element={<PrivateRoute roles={["mesero", "administrador", "cajero"]} />}>
        <Route path="/mesas" element={<MesasPage />} />
        <Route path="/mesas/:id" element={<OrdenPage />} />
        <Route path="/caja/:id" element={<CajaPage />} />
      </Route>
      <Route element={<PrivateRoute roles={["cocinero", "chef"]} />}>
        <Route path="/cocina" element={<CocinaPage />} />
      </Route>
      <Route element={<PrivateRoute roles={["cajero", "administrador"]} />}>
        <Route path="/caja" element={<Navigate to="/mesas" replace />} />
        <Route path="/cierre-caja" element={<CierreCajaPage />} />
        <Route path="/finanzas" element={<FinanzasPage />} />
        <Route path="/bold-prueba" element={<BoldTestPage />} />
      </Route>
      <Route element={<PrivateRoute roles={["chef", "administrador", "mesero", "cajero"]} />}>
        <Route path="/recetario" element={<RecetarioPage />} />
        <Route path="/inventario" element={<InventarioPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}
