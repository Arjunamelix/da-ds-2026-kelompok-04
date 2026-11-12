/**
 * ==============================================================================
 * HALAMAN: ANALISIS VISUALISASI MENDALAM (Analisis.jsx)
 * ==============================================================================
 * Fungsi:
 * - Visualisasi eksploratif Data Analytics tingkat lanjut.
 * - Berisi Heatmap korelasi/anomali, BoxPlot sebaran harga, SmallMultiples,
 *   dan Treemap sebaran pasar di wilayah Kota Medan.
 *
 * Endpoint API yang digunakan:
 * - GET /api/wh/* (diatur di backend: internal/handler/analitik_wh.go)
 * ==============================================================================
 */

import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api } from '../api/client.js'
import { useApp } from '../AppContext.jsx'
import { Galat, Kosong, Memuat, PilihKecamatan, PilihKomoditas } from '../components/Umum.jsx'
import BoxPlot from '../components/viz/BoxPlot.jsx'
import DeretBeranotasi from '../components/viz/DeretBeranotasi.jsx'
import Heatmap, { LegendaDivergen } from '../components/viz/Heatmap.jsx'
import SmallMultiples from '../components/viz/SmallMultiples.jsx'
import TreemapWilayah from '../components/viz/TreemapWilayah.jsx'
import { useMuat } from '../components/viz/useMuat.js'
import {
  CATATAN_DATA, RENTANG, WARNA, fmtAngka, fmtPct, fmtRp, hitungRentang, labelBulan, labelBulanPendek, labelTanggal,
  rentangBulan, teksDiAtas, warnaDivergen,
} from '../components/viz/util.js'
import '../components/viz/viz.css'

// Halaman analisis mendalam. Semua grafik di halaman ini memakai satu filter global
// (komoditas, kecamatan, rentang waktu) yang tersimpan di URL, sehingga tampilan bisa dibagikan.
// Klik pada satu grafik mengubah filter global dan ikut menyaring grafik lain (filter silang):
//   peta panas -> komoditas dan bulan, small multiples -> komoditas,
//   box plot -> bulan (telusur ke satu bulan), treemap -> kecamatan (telusur kota > kecamatan > pasar).

function Panel({ judul, sub, children }) {
  return (
    <div className="panel vz-panel">
      <h2>{judul}</h2>
      {sub && <p className="vz-sub">{sub}</p>}
      {children}
    </div>
  )
}

function Status({ st, kosong, children }) {
  if (st.galat) return <Galat pesan={st.galat.message} detail={st.galat.detail} />
  if (!st.data) return <Memuat />
  if (kosong) return <Kosong>{kosong}</Kosong>
  return children
}

export default function Analisis() {
  const { ref, versiModel } = useApp()
  const [params, setParams] = useSearchParams()
  const [metrik, setMetrik] = useState('indeks')

  const bawaanKom = ref.komoditas.some((k) => k.kode === 'cabai_merah') ? 'cabai_merah' : ref.komoditas[0].kode
  const komoditas = params.get('komoditas') || bawaanKom
  const kecamatan = params.get('kecamatan') || ''
  const rentang = params.get('rentang') || '12b'
  const bulan = params.get('bulan') || ''
  const namaKom = (kode) => ref.komoditas.find((k) => k.kode === kode)?.nama ?? kode
  const kom = ref.komoditas.find((k) => k.kode === komoditas)

  const ubah = (perubahan) => {
    const p = new URLSearchParams(params)
    for (const [k, v] of Object.entries(perubahan)) {
      if (v) p.set(k, v)
      else p.delete(k)
    }
    setParams(p, { replace: true })
  }

  // tanggal data terakhir (patokan rentang waktu)
  const kpi = useMuat(() => api.analitik.kpi(), `kpi|${versiModel}`)
  const tAkhir = kpi.data?.tanggal
  const { dari, sampai } = rentang === 'bulan' && bulan ? rentangBulan(bulan) : hitungRentang(rentang, tAkhir)
  const siap = !!tAkhir || rentang === 'semua' || rentang === 'bulan'
  const kunciWaktu = `${dari}|${sampai}|${versiModel}|${siap}`

  const tunggu = () => new Promise(() => {})
  const heat = useMuat(() => (siap ? api.analitik.heatmap({ dari, sampai }) : tunggu()), `heat|${kunciWaktu}`)
  const deret = useMuat(() => (siap ? api.analitik.deret({ komoditas, kecamatan, dari, sampai }) : tunggu()), `deret|${komoditas}|${kecamatan}|${kunciWaktu}`)
  const sebaran = useMuat(() => (siap ? api.analitik.sebaran({ komoditas, kecamatan, dari, sampai }) : tunggu()), `seb|${komoditas}|${kecamatan}|${kunciWaktu}`)
  const wilayah = useMuat(() => (siap ? api.analitik.wilayah({ komoditas, dari, sampai }) : tunggu()), `wil|${komoditas}|${kunciWaktu}`)
  const mingguan = useMuat(() => (siap ? api.analitik.mingguan({ dari, sampai }) : tunggu()), `mg|${kunciWaktu}`)
  const stat = useMuat(() => (siap ? api.analitik.statistik({ dari, sampai }) : tunggu()), `stat|${kunciWaktu}`)

  // --- peta panas komoditas x bulan ---
  const petaPanas = useMemo(() => {
    const sel = heat.data?.sel ?? []
    const barisMap = new Map()
    const kolomSet = new Set()
    const nilai = new Map()
    for (const s of sel) {
      if (!barisMap.has(s.komoditas)) barisMap.set(s.komoditas, { kunci: s.komoditas, label: s.nama, kategori: s.kategori })
      kolomSet.add(s.tahun_bulan)
      nilai.set(`${s.komoditas}|${s.tahun_bulan}`, s)
    }
    const kolom = [...kolomSet].sort().map((tb) => ({ kunci: tb, label: labelBulan(tb) }))
    return { baris: [...barisMap.values()], kolom, nilai }
  }, [heat.data])

  // --- korelasi ---
  const korelasi = useMemo(() => {
    const rows = stat.data?.korelasi ?? []
    const m = new Map(rows.map((r) => [`${r.komoditas_a}|${r.komoditas_b}`, r]))
    const kodes = [...new Set(rows.map((r) => r.komoditas_a))]
    const urut = ref.komoditas.map((k) => k.kode).filter((k) => kodes.includes(k))
    return { m, baris: urut.map((k) => ({ kunci: k, label: namaKom(k) })) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stat.data, ref])

  const labelRentang = rentang === 'bulan' && bulan ? labelBulan(bulan) : RENTANG.find((r) => r.kode === rentang)?.label
  const satuan = kom?.satuan ?? 'kg'
  const tanpaKota = deret.data?.catatan

  return (
    <>
      <div className="bar-judul">
        <h1>Analisis mendalam</h1>
      </div>

      {/* ---------------- filter global ---------------- */}
      <div className="vz-filter" role="region" aria-label="Filter global">
        <PilihKomoditas nilai={komoditas} onChange={(v) => ubah({ komoditas: v })} referensi={ref} id="an-kom" />
        <PilihKecamatan nilai={kecamatan || ref.kota.kecamatan} onChange={(v) => ubah({ kecamatan: v === ref.kota.kecamatan ? '' : v })} referensi={ref} id="an-kec" />
        <div className="field">
          <span>Rentang waktu</span>
          <div className="segmen" role="group" aria-label="Rentang waktu">
            {RENTANG.map((r) => (
              <button key={r.kode} type="button" className={rentang === r.kode ? 'aktif' : ''} onClick={() => ubah({ rentang: r.kode, bulan: '' })}>
                {r.label}
              </button>
            ))}
          </div>
        </div>
        {rentang === 'bulan' && bulan && (
          <span className="vz-chip">
            Bulan: {labelBulan(bulan)}
            <button type="button" aria-label="Hapus filter bulan" onClick={() => ubah({ rentang: '12b', bulan: '' })}>
              ×
            </button>
          </span>
        )}
        {kecamatan && (
          <span className="vz-chip">
            Kecamatan: {kecamatan}
            <button type="button" aria-label="Hapus filter kecamatan" onClick={() => ubah({ kecamatan: '' })}>
              ×
            </button>
          </span>
        )}
        <p className="vz-filter-ket">
          Filter ini berlaku untuk semua grafik di halaman. Klik sel peta panas, kotak bulan, atau kecamatan di treemap untuk menyaring grafik lain.
          {tAkhir && ` Data terakhir: ${labelTanggal(tAkhir)}.`}
        </p>
      </div>

      {/* ---------------- 1. peta panas ---------------- */}
      <Panel
        judul={metrik === 'indeks' ? 'Pola musiman: harga bulanan dibanding rata-rata komoditasnya' : 'Perubahan harga dari bulan ke bulan'}
        sub={`${labelRentang} · median harga pasar se-Kota Medan · klik sel untuk memilih komoditas dan bulan itu`}
      >
        <div className="segmen" role="group" aria-label="Ukuran peta panas" style={{ marginBottom: 10 }}>
          <button type="button" className={metrik === 'indeks' ? 'aktif' : ''} onClick={() => setMetrik('indeks')}>
            Indeks (rata-rata = 100)
          </button>
          <button type="button" className={metrik === 'perubahan' ? 'aktif' : ''} onClick={() => setMetrik('perubahan')}>
            Perubahan bulanan
          </button>
        </div>
        <Status st={heat} kosong={heat.data && !petaPanas.baris.length ? 'Tidak ada data pada rentang ini.' : null}>
          <Heatmap
            judulAria="Peta panas harga komoditas per bulan"
            baris={petaPanas.baris}
            kolom={petaPanas.kolom}
            lebarSel={petaPanas.kolom.length > 14 ? 28 : 46}
            labelKolom={(k, i) => (petaPanas.kolom.length > 14 ? (i % 3 === 0 ? labelBulanPendek(k.kunci) : '') : labelBulanPendek(k.kunci))}
            nilai={(b, k) => {
              const s = petaPanas.nilai.get(`${b}|${k}`)
              if (!s) return null
              return metrik === 'indeks' ? s.indeks : s.perubahan_bulanan_pct
            }}
            warna={(v) => (metrik === 'indeks' ? warnaDivergen(v - 100, 20) : warnaDivergen(v, 10))}
            warnaTeks={teksDiAtas}
            labelSel={petaPanas.kolom.length <= 14 ? (v) => fmtAngka(v, 0) : null}
            barisAktif={komoditas}
            kolomAktif={bulan}
            onKlikBaris={(b) => ubah({ komoditas: b.kunci })}
            onKlikSel={(b, k) => ubah({ komoditas: b.kunci, rentang: 'bulan', bulan: k.kunci })}
            isiTooltip={(b, k) => {
              const s = petaPanas.nilai.get(`${b.kunci}|${k.kunci}`)
              return (
                <>
                  <strong>
                    {b.label} · {k.label}
                  </strong>
                  Rata-rata {fmtRp(s.rata)}
                  <br />
                  Indeks {fmtAngka(s.indeks, 1)} ({fmtPct(s.indeks - 100)} dari rata-rata periode)
                  <br />
                  {s.perubahan_bulanan_pct != null && (
                    <>
                      Dibanding bulan sebelumnya {fmtPct(s.perubahan_bulanan_pct)}
                      <br />
                    </>
                  )}
                  {s.hari} hari berdata
                </>
              )
            }}
          />
          {metrik === 'indeks' ? (
            <LegendaDivergen kiri="lebih murah (≤ 80)" kanan="lebih mahal (≥ 120)" tengah="100, rata-rata periode" warnaKiri={WARNA.biru} warnaTengah={WARNA.netral} warnaKanan={WARNA.oranye} />
          ) : (
            <LegendaDivergen kiri="turun ≥ 10%" kanan="naik ≥ 10%" tengah="tidak berubah" warnaKiri={WARNA.biru} warnaTengah={WARNA.netral} warnaKanan={WARNA.oranye} />
          )}
        </Status>
      </Panel>

      {/* ---------------- 2. deret beranotasi ---------------- */}
      <Panel
        judul={`Harga harian ${namaKom(komoditas)} ${kecamatan ? `di ${kecamatan}` : 'se-Kota Medan'}, dengan hari besar dan lonjakan`}
        sub={`${labelRentang} · ${kecamatan ? 'rata-rata harga pasar di kecamatan' : 'median harga pasar (hari dengan minimal 3 pasar melapor)'}`}
      >
        <Status st={deret} kosong={deret.data && deret.data.titik.length < 2 ? tanpaKota || 'Tidak ada data harian untuk pilihan ini.' : null}>
          <DeretBeranotasi titik={deret.data?.titik ?? []} hariBesar={deret.data?.hari_besar ?? []} satuan={satuan} />
          {CATATAN_DATA[komoditas] && <p className="catatan">Catatan data: {CATATAN_DATA[komoditas]}.</p>}
        </Status>
      </Panel>

      {/* ---------------- 3. box plot + treemap ---------------- */}
      <div className="dua-kolom">
        <Panel
          judul={`Sebaran harga ${namaKom(komoditas)} antarpasar per bulan`}
          sub={`Kotak = separuh pasar di tengah, garis = median, kumis = 5% sampai 95% · ${kecamatan || 'semua kecamatan'} · klik bulan untuk menelusuri`}
        >
          <Status st={sebaran} kosong={sebaran.data && !sebaran.data.bulan.length ? 'Tidak ada data untuk pilihan ini.' : null}>
            <BoxPlot data={sebaran.data?.bulan} satuan={satuan} bulanAktif={bulan} onKlikBulan={(tb) => ubah({ rentang: 'bulan', bulan: tb })} />
          </Status>
        </Panel>
        <Panel
          judul={`Kelengkapan laporan dan tingkat harga ${namaKom(komoditas)} per wilayah`}
          sub="Luas = banyak laporan harga · warna = rata-rata selisih terhadap median kota (biru lebih murah, oranye lebih mahal)"
        >
          <Status st={wilayah} kosong={wilayah.data && !wilayah.data.pasar.length ? 'Tidak ada laporan pada rentang ini.' : null}>
            <TreemapWilayah
              pasar={wilayah.data?.pasar ?? []}
              kecamatan={kecamatan}
              satuKomoditas
              jumlahKecamatanSemua={ref.kecamatan.length}
              onPilihKecamatan={(k) => ubah({ kecamatan: k })}
            />
            <LegendaDivergen kiri="≤ −10%" kanan="≥ +10%" tengah="sama dengan median kota" warnaKiri={WARNA.biru} warnaTengah={WARNA.netral} warnaKanan={WARNA.oranye} />
          </Status>
        </Panel>
      </div>

      {/* ---------------- 4. small multiples ---------------- */}
      <Panel
        judul="Tren mingguan semua komoditas"
        sub={`${labelRentang} · tiap panel memakai skala harganya sendiri (rentang minimal 10% dari harga), jadi yang dibandingkan adalah pola naik-turunnya · klik panel untuk memilih komoditas`}
      >
        <Status st={mingguan}>
          <SmallMultiples titik={mingguan.data?.titik ?? []} komoditasAktif={komoditas} onPilih={(k) => ubah({ komoditas: k })} />
        </Status>
      </Panel>

      {/* ---------------- 5. korelasi ---------------- */}
      <Panel
        judul="Komoditas mana yang harganya bergerak bersama?"
        sub={`Korelasi perubahan harga mingguan (−1 sampai 1) · ${labelRentang} · minimal 12 minggu berurutan`}
      >
        <Status st={stat} kosong={stat.data && !korelasi.baris.length ? 'Rentang terlalu pendek untuk menghitung korelasi (butuh minimal 12 minggu).' : null}>
          <Heatmap
            judulAria="Peta panas korelasi antarkomoditas"
            baris={korelasi.baris}
            kolom={korelasi.baris}
            lebarSel={46}
            lebarLabel={150}
            kolomTegak
            nilai={(a, b) => korelasi.m.get(`${a}|${b}`)?.korelasi ?? null}
            warna={(v) => warnaDivergen(v, 1, { positif: WARNA.biru, negatif: WARNA.oranye })}
            warnaTeks={teksDiAtas}
            labelSel={(v) => fmtAngka(v, 2)}
            barisAktif={komoditas}
            onKlikBaris={(b) => ubah({ komoditas: b.kunci })}
            isiTooltip={(a, b, v) => (
              <>
                <strong>
                  {a.label} × {b.label}
                </strong>
                Korelasi {fmtAngka(v, 2)} dari {korelasi.m.get(`${a.kunci}|${b.kunci}`)?.minggu} minggu
                <br />
                {Math.abs(v) < 0.2 ? 'hampir tidak berhubungan' : v > 0 ? 'cenderung naik dan turun bersama' : 'cenderung bergerak berlawanan'}
              </>
            )}
          />
          <LegendaDivergen kiri="−1 berlawanan" kanan="+1 bergerak bersama" tengah="0, tidak berhubungan" warnaKiri={WARNA.oranye} warnaTengah={WARNA.netral} warnaKanan={WARNA.biru} />
        </Status>
      </Panel>
    </>
  )
}
