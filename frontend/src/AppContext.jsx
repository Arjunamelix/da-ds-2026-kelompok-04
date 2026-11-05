import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { api } from './api/client.js'

const Ctx = createContext(null)
export const useApp = () => useContext(Ctx)

export function AppProvider({ children }) {
  const [ref, setRef] = useState(null)
  const [galatRef, setGalatRef] = useState(null)
  const [hitung, setHitung] = useState(null)
  const [versiTampilan, setVersiTampilan] = useState(0)
  const timer = useRef(null)

  useEffect(() => {
    api.referensi().then(setRef).catch((e) => setGalatRef(e.message))
  }, [])

  const segarkan = useCallback(async () => {
    try {
      const h = await api.statusHitung()
      setHitung(h)
      setVersiTampilan((v) => (h.versi_model !== v ? h.versi_model : v))
      return h
    } catch {
      return null
    }
  }, [])

  // Polling: rapat saat menghitung atau model tertinggal dari data, jarang saat tenang.
  useEffect(() => {
    let batal = false
    const putaran = async () => {
      const h = await segarkan()
      if (batal) return
      const sibuk = h && (h.status_hitung === 'running' || h.versi_model !== h.versi_data)
      timer.current = setTimeout(putaran, sibuk ? 2000 : 15000)
    }
    putaran()
    return () => {
      batal = true
      clearTimeout(timer.current)
    }
  }, [segarkan])

  // Dipanggil setelah menulis data agar polling cepat langsung berjalan.
  const picuPolling = useCallback(() => {
    clearTimeout(timer.current)
    segarkan().then(() => {
      timer.current = setTimeout(function ulang() {
        segarkan().then((h) => {
          const sibuk = h && (h.status_hitung === 'running' || h.versi_model !== h.versi_data)
          timer.current = setTimeout(ulang, sibuk ? 2000 : 15000)
        })
      }, 1500)
    })
  }, [segarkan])

  // Status pengambilan data otomatis (layanan scraper). Rapat saat menarik data, jarang saat tenang.
  // Galat (mis. 503 bila layanan scraper belum dinyalakan) tidak mengganggu halaman lain.
  const [scraper, setScraper] = useState(null)
  const [galatScraper, setGalatScraper] = useState(null)
  const timerScraper = useRef(null)
  const tadiBerjalan = useRef(false)

  const segarkanScraper = useCallback(async () => {
    try {
      const s = await api.scraper.status()
      setScraper(s)
      setGalatScraper(null)
      // Tarikan baru selesai dan menambah data: model akan dilatih ulang, jadi percepat polling status model.
      if (tadiBerjalan.current && !s.sedang_berjalan && s.terakhir?.baris_baru > 0) picuPolling()
      tadiBerjalan.current = !!s.sedang_berjalan
      return s
    } catch (e) {
      setGalatScraper(e)
      return null
    }
  }, [picuPolling])

  // Satu putaran polling; genScraper mencegah dua putaran berjalan bersamaan setelah tombol ditekan.
  const genScraper = useRef(0)
  const putarScraper = useRef(null)
  useEffect(() => {
    let batal = false
    const putaran = async () => {
      const g = ++genScraper.current
      clearTimeout(timerScraper.current)
      const s = await segarkanScraper()
      if (batal || g !== genScraper.current) return
      timerScraper.current = setTimeout(putaran, s?.sedang_berjalan ? 5000 : 60000)
    }
    putarScraper.current = putaran
    putaran()
    return () => {
      batal = true
      clearTimeout(timerScraper.current)
    }
  }, [segarkanScraper])

  // Tombol "Ambil data sekarang": mulai tarikan lalu langsung pantau (setiap 5 detik selama berjalan).
  const ambilDataSekarang = useCallback(async () => {
    await api.scraper.jalankan()
    tadiBerjalan.current = true
    genScraper.current++
    clearTimeout(timerScraper.current)
    timerScraper.current = setTimeout(() => putarScraper.current?.(), 1500)
  }, [])

  const menghitung = !!hitung && (hitung.status_hitung === 'running' || (hitung.status_hitung !== 'error' && hitung.versi_model !== hitung.versi_data))

  return (
    <Ctx.Provider
      value={{
        ref, galatRef, hitung, menghitung, versiModel: versiTampilan, segarkan, picuPolling,
        scraper, galatScraper, segarkanScraper, ambilDataSekarang,
      }}
    >
      {children}
    </Ctx.Provider>
  )
}