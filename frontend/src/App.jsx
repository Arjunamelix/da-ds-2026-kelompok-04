import { Route, Routes } from 'react-router-dom'
import { AppProvider } from './AppContext.jsx'
import Layout from './components/Layout.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Tren from './pages/Tren.jsx'
import Perbandingan from './pages/Perbandingan.jsx'
import Prediksi from './pages/Prediksi.jsx'
import KelolaData from './pages/KelolaData.jsx'


export default function App() {
  return (
    <AppProvider>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="tren" element={<Tren />} />
          <Route path="perbandingan" element={<Perbandingan />} />
          <Route path="prediksi" element={<Prediksi />} />
          <Route path="kelola" element={<KelolaData />} />
          <Route path="*" element={<div className="kosong">Halaman tidak ditemukan.</div>} />
        </Route>
      </Routes>
    </AppProvider>
  )
}