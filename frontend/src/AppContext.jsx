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

  const menghitung = !!hitung && (hitung.status_hitung === 'running' || (hitung.status_hitung !== 'error' && hitung.versi_model !== hitung.versi_data))

  return (
    <Ctx.Provider value={{ ref, galatRef, hitung, menghitung, versiModel: versiTampilan, segarkan, picuPolling }}>
      {children}
    </Ctx.Provider>
  )
}