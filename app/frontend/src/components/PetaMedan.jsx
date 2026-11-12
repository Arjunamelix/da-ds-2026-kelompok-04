import React, { useEffect, useMemo, useRef, useState } from 'react'
import { rupiah } from '../lib/format.js'
import medanGeoJson from '../data/medan_kecamatan.json'

const GOOGLE_MAPS_API_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY || 'AIzaSyDqJKUJ0_qiin7JesOIsqCoLnBfMzk_jMg'

// Kategori warna berdasarkan selisih persentase vs rata-rata Kota Medan
export function getWarnaKategori(selisihPct, tanpaData) {
  if (tanpaData || selisihPct == null) {
    return {
      bg: '#94a3b8',
      stroke: '#64748b',
      label: 'Tanpa Data',
      kategori: 'Tanpa Data',
      textColor: '#ffffff',
    }
  }
  if (selisihPct < -5) {
    return {
      bg: '#22c55e', // Hijau (Rendah)
      stroke: '#15803d',
      label: 'Rendah',
      kategori: 'Rendah',
      textColor: '#ffffff',
    }
  }
  if (selisihPct <= 0) {
    return {
      bg: '#84cc16', // Hijau Muda (Rendah-Sedang)
      stroke: '#4d7c0f',
      label: 'Rendah-Sedang',
      kategori: 'Rendah-Sedang',
      textColor: '#ffffff',
    }
  }
  if (selisihPct <= 5) {
    return {
      bg: '#eab308', // Kuning (Sedang)
      stroke: '#a16207',
      label: 'Sedang',
      kategori: 'Sedang',
      textColor: '#ffffff',
    }
  }
  return {
    bg: '#ef4444', // Merah (Tinggi/Lonjakan)
    stroke: '#b91c1c',
    label: 'Tinggi',
    kategori: 'Tinggi',
    textColor: '#ffffff',
  }
}

// Styling Peta Google Maps Mode Gelap Modern
const DARK_MAP_STYLE = [
  { elementType: 'geometry', stylers: [{ color: '#161e2e' }] },
  { elementType: 'labels.text.stroke', stylers: [{ color: '#0f172a' }, { weight: 3 }] },
  { elementType: 'labels.text.fill', stylers: [{ color: '#94a3b8' }] },
  {
    featureType: 'administrative.locality',
    elementType: 'labels.text.fill',
    stylers: [{ color: '#cbd5e1' }],
  },
  {
    featureType: 'poi',
    stylers: [{ visibility: 'off' }],
  },
  {
    featureType: 'road',
    elementType: 'geometry',
    stylers: [{ color: '#27354a' }],
  },
  {
    featureType: 'road',
    elementType: 'geometry.stroke',
    stylers: [{ color: '#161e2e' }],
  },
  {
    featureType: 'road',
    elementType: 'labels.text.fill',
    stylers: [{ color: '#64748b' }],
  },
  {
    featureType: 'transit',
    stylers: [{ visibility: 'off' }],
  },
  {
    featureType: 'water',
    elementType: 'geometry',
    stylers: [{ color: '#090d16' }],
  },
]

// Loader Google Maps JavaScript SDK
function muatGoogleMaps(apiKey) {
  return new Promise((resolve, reject) => {
    if (window.google?.maps) {
      resolve(window.google.maps)
      return
    }
    const scriptId = 'google-maps-api-script'
    const existing = document.getElementById(scriptId)
    if (existing) {
      existing.addEventListener('load', () => resolve(window.google.maps))
      existing.addEventListener('error', () => reject(new Error('Gagal memuat Google Maps SDK')))
      return
    }
    const script = document.createElement('script')
    script.id = scriptId
    script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=geometry`
    script.async = true
    script.defer = true
    script.onload = () => resolve(window.google.maps)
    script.onerror = () => reject(new Error('Koneksi Google Maps gagal. Pastikan API key aktif.'))
    document.head.appendChild(script)
  })
}

export default function PetaMedan({ dataPerbandingan, namaKomoditas, kecamatanTerpilih = [], onPilihKecamatan }) {
  const mapContainerRef = useRef(null)
  const mapInstanceRef = useRef(null)
  const markersRef = useRef([])
  const boundsRef = useRef(null)

  const [statusPeta, setStatusPeta] = useState({ memuat: true, galat: null })
  const [hovered, setHovered] = useState(null)
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 })

  // Peta data kecamatan dari API perbandingan
  const dataMap = useMemo(() => {
    const m = {}
    if (dataPerbandingan?.kecamatan) {
      dataPerbandingan.kecamatan.forEach((k) => {
        m[k.kecamatan] = k
      })
    }
    return m
  }, [dataPerbandingan])

  // Inisialisasi Peta Google Maps
  useEffect(() => {
    let aktif = true

    muatGoogleMaps(GOOGLE_MAPS_API_KEY)
      .then((maps) => {
        if (!aktif || !mapContainerRef.current) return

        if (!mapInstanceRef.current) {
          const map = new maps.Map(mapContainerRef.current, {
            center: { lat: 3.5952, lng: 98.6722 },
            zoom: 11,
            styles: DARK_MAP_STYLE,
            disableDefaultUI: false,
            mapTypeControl: false,
            streetViewControl: false,
            fullscreenControl: true,
            zoomControl: true,
          })

          mapInstanceRef.current = map

          // Tambahkan layer GeoJSON batas 21 kecamatan
          map.data.addGeoJson(medanGeoJson)

          // Hitung batas kota Medan dan sesuaikan view
          const bounds = new maps.LatLngBounds()
          medanGeoJson.features.forEach((feat) => {
            const [lat, lng] = feat.properties.center
            bounds.extend(new maps.LatLng(lat, lng))

            // Tambahkan label teks nama kecamatan
            const marker = new maps.Marker({
              position: { lat, lng },
              map: map,
              icon: {
                path: maps.SymbolPath.CIRCLE,
                scale: 0,
              },
              label: {
                text: feat.properties.nama,
                color: '#ffffff',
                fontSize: '10.5px',
                fontWeight: '600',
                className: 'peta-marker-label',
              },
              clickable: false,
            })
            markersRef.current.push(marker)
          })

          boundsRef.current = bounds
          map.fitBounds(bounds)

          // Event Listener interaktif pada poligon kecamatan
          map.data.addListener('mouseover', (e) => {
            const nama = e.feature.getProperty('nama')
            setHovered(nama)
          })

          map.data.addListener('mousemove', (e) => {
            if (mapContainerRef.current && e.domEvent) {
              const rect = mapContainerRef.current.getBoundingClientRect()
              setMousePos({
                x: e.domEvent.clientX - rect.left + 15,
                y: e.domEvent.clientY - rect.top + 15,
              })
            }
          })

          map.data.addListener('mouseout', () => {
            setHovered(null)
          })

          map.data.addListener('click', (e) => {
            const nama = e.feature.getProperty('nama')
            if (onPilihKecamatan) {
              onPilihKecamatan(nama)
            }
          })
        }

        setStatusPeta({ memuat: false, galat: null })
      })
      .catch((err) => {
        if (aktif) {
          setStatusPeta({ memuat: false, galat: err.message })
        }
      })

    return () => {
      aktif = false
    }
  }, [])

  // Perbarui style poligon ketika data/filter berubah
  useEffect(() => {
    const map = mapInstanceRef.current
    if (!map) return

    map.data.setStyle((feature) => {
      const nama = feature.getProperty('nama')
      const kData = dataMap[nama]
      const warna = getWarnaKategori(kData?.selisih_pct_vs_kota, !kData || kData.tanpa_data)
      const isSelected = kecamatanTerpilih.includes(nama)
      const isHovered = hovered === nama

      return {
        fillColor: warna.bg,
        fillOpacity: isHovered ? 0.88 : isSelected ? 0.78 : 0.58,
        strokeColor: isSelected ? '#38bdf8' : isHovered ? '#ffffff' : '#334155',
        strokeWeight: isSelected ? 3.5 : isHovered ? 2.5 : 1,
        zIndex: isHovered ? 10 : isSelected ? 5 : 1,
        cursor: 'pointer',
      }
    })
  }, [dataMap, kecamatanTerpilih, hovered])

  const handleResetView = () => {
    if (mapInstanceRef.current && boundsRef.current) {
      mapInstanceRef.current.fitBounds(boundsRef.current)
    }
  }

  const hoveredData = hovered ? dataMap[hovered] : null
  const hoveredWarna = hoveredData ? getWarnaKategori(hoveredData.selisih_pct_vs_kota, hoveredData.tanpa_data) : null

  return (
    <div className="peta-wrapper">
      <div className="peta-kepala" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h3>Peta Distribusi Harga per Kecamatan (Google Maps)</h3>
          <p className="peta-subjudul">
            Batas geografis nyata 21 kecamatan Kota Medan. Arahkan kursor ke wilayah untuk melihat rincian harga pasar, atau klik untuk filter grafik.
          </p>
        </div>
        <button type="button" className="peta-btn-reset" onClick={handleResetView} title="Kembalikan tampilan peta ke seluruh Kota Medan">
          ⟲ Reset Zoom
        </button>
      </div>

      <div className="peta-container" style={{ padding: 0, overflow: 'hidden' }}>
        {statusPeta.memuat && (
          <div className="peta-loading-overlay">
            <span className="spinner" /> Memuat Google Maps...
          </div>
        )}

        {statusPeta.galat && (
          <div className="peta-error-overlay">
            <p>⚠️ {statusPeta.galat}</p>
            <small>Silakan periksa konfigurasi API Key Google Maps pada file app/frontend/.env</small>
          </div>
        )}

        <div
          ref={mapContainerRef}
          className="peta-gmaps-canvas"
          style={{ width: '100%', height: '560px', borderRadius: 'inherit' }}
        />

        {/* Tooltip Melayang Interaktif */}
        {hovered && hoveredData && (
          <div
            className="peta-tooltip-card"
            style={{
              left: `${Math.min(mousePos.x, (mapContainerRef.current?.clientWidth || 500) - 250)}px`,
              top: `${Math.max(10, Math.min(mousePos.y - 40, (mapContainerRef.current?.clientHeight || 500) - 220))}px`,
            }}
          >
            <div className="tooltip-title">{hovered}</div>
            <div className="tooltip-commodity">{namaKomoditas}</div>

            {hoveredData.tanpa_data ? (
              <div className="tooltip-kosong">
                <em>Tidak ada data pasar di SIMPANG untuk kecamatan ini</em>
              </div>
            ) : (
              <>
                <div className="tooltip-price-group">
                  <div className="tooltip-price-label">Harga Rata-rata:</div>
                  <div className="tooltip-price-value" style={{ color: hoveredWarna.bg }}>
                    {rupiah(hoveredData.harga)}
                  </div>
                  <div className="tooltip-status-badge" style={{ color: hoveredWarna.bg }}>
                    ({hoveredWarna.kategori})
                  </div>
                </div>

                <div className="tooltip-market-count">
                  <strong>Jumlah Pasar:</strong> {hoveredData.jumlah_pasar || (hoveredData.detail_pasar?.length ?? 1)}
                </div>

                {hoveredData.detail_pasar && hoveredData.detail_pasar.length > 0 && (
                  <div className="tooltip-market-details">
                    <hr className="tooltip-divider" />
                    <div className="tooltip-detail-header">Detail Pasar:</div>
                    <ul className="tooltip-market-list">
                      {hoveredData.detail_pasar.map((p) => (
                        <li key={p.nama_pasar}>
                          • {p.nama_pasar}: <span>{rupiah(p.harga)}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>

      {/* Legend Warna Peta */}
      <div className="peta-legend">
        <span className="legend-label">Indikator Harga:</span>
        <div className="legend-item">
          <span className="legend-box" style={{ background: '#22c55e' }} />
          <span>Rendah (&lt; -5%)</span>
        </div>
        <div className="legend-item">
          <span className="legend-box" style={{ background: '#84cc16' }} />
          <span>Rendah-Sedang</span>
        </div>
        <div className="legend-item">
          <span className="legend-box" style={{ background: '#eab308' }} />
          <span>Sedang (Wajar)</span>
        </div>
        <div className="legend-item">
          <span className="legend-box" style={{ background: '#ef4444' }} />
          <span>Tinggi / Lonjakan</span>
        </div>
        <div className="legend-item">
          <span className="legend-box" style={{ background: '#94a3b8', border: '1px solid #64748b' }} />
          <span>Tanpa Data</span>
        </div>
      </div>
    </div>
  )
}
