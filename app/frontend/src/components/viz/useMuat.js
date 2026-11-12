import { useEffect, useState } from 'react'

// Memuat data dari API dan membatalkan hasil lama bila parameter berubah.
// kunci: string yang berubah bila permintaan perlu diulang (gabungan parameter dan versi model).
export function useMuat(fn, kunci) {
  const [state, setState] = useState({ data: null, galat: null, memuat: true })
  useEffect(() => {
    let batal = false
    setState((s) => ({ data: s.data, galat: null, memuat: true }))
    // Promise.resolve().then(fn): galat sinkron (mis. fungsi API belum ada di tes) ikut tertangkap.
    Promise.resolve()
      .then(fn)
      .then((data) => !batal && setState({ data, galat: null, memuat: false }))
      .catch((galat) => !batal && setState({ data: null, galat, memuat: false }))
    return () => {
      batal = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [kunci])
  return state
}
