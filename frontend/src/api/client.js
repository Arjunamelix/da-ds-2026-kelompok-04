// Pemanggil API Go. Kontrak lengkap: docs/kontrak_api.md
const BASE = (import.meta.env.VITE_API_URL ?? '') + '/api'

export class ApiError extends Error {
  constructor(pesan, { status, detail } = {}) {
    super(pesan)
    this.status = status
    this.detail = detail || []
  }
}

async function req(path, opts = {}) {
  let resp
  try {
    resp = await fetch(BASE + path, opts)
  } catch {
    throw new ApiError('Backend tidak terjangkau. Pastikan API Go berjalan.', { status: 0 })
  }
  if (!resp.ok) {
    let body = {}
    try {
      body = await resp.json()
    } catch {
      /* balasan bukan JSON */
    }
    throw new ApiError(body.error || `Permintaan gagal (${resp.status})`, { status: resp.status, detail: body.detail })
  }
  return resp.json()
}

const json = (method, body) => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

export function qs(obj) {
  const p = new URLSearchParams()
  for (const [k, v] of Object.entries(obj)) {
    if (v === undefined || v === null || v === '') continue
    if (Array.isArray(v)) v.forEach((x) => p.append(k, x))
    else p.append(k, v)
  }
  const s = p.toString()
  return s ? '?' + s : ''
}

export const api = {
  referensi: () => req('/referensi'),
  ringkasan: (kecamatan) => req('/ringkasan' + qs({ kecamatan })),
  tren: ({ komoditas, kecamatan, dari, sampai }) => req('/tren' + qs({ komoditas, kecamatan, dari, sampai })),
  perbandingan: ({ komoditas, tanggal }) => req('/perbandingan' + qs({ komoditas, tanggal })),
  prediksi: ({ komoditas, kecamatan }) => req('/prediksi' + qs({ komoditas, kecamatan })),
  prediksiSesudah: (kunci) => req('/prediksi/sesudah', json('POST', kunci)),
  status: (kecamatan) => req('/status' + qs({ kecamatan })),
  evaluasi: (komoditas) => req('/evaluasi' + qs({ komoditas })),
  statusHitung: () => req('/status-hitung'),
  versiData: () => req('/versi-data'),
  latihUlang: () => req('/retrain', { method: 'POST' }),

  listHarga: (f) => req('/harga' + qs(f)),
  tambahHarga: (d) => req('/harga', json('POST', d)),
  ubahHarga: (id, d) => req(`/harga/${id}`, json('PUT', d)),
  hapusHarga: (id) => req(`/harga/${id}`, { method: 'DELETE' }),
  imporHarga: (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return req('/harga/import', { method: 'POST', body: fd })
  },
  urlEkspor: (f) => BASE + '/harga/export' + qs(f),
  urlTemplate: () => BASE + '/harga/template',
}