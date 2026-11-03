import { Bar, BarChart, CartesianGrid, Cell, LabelList, Legend, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Link } from 'react-router-dom'
import { api } from '../api/client.js'
import { useApp } from '../AppContext.jsx'
import { Galat, Memuat } from '../components/Umum.jsx'
import { useMuat } from '../components/viz/useMuat.js'
import { CATATAN_DATA, WARNA, domainBerlabel, fmtAngka, fmtPct, labelTanggal } from '../components/viz/util.js'
import '../components/viz/viz.css'

// Halaman storytelling: lima temuan utama dengan judul grafik berupa temuannya sendiri.
// Angka di judul dihitung dari data terbaru, jadi tetap benar ketika data bertambah.

const tinggiBatang = (n) => Math.max(200, n * 28 + 40)

function Temuan({ no, judul, children, artinya }) {
  return (
    <article className="panel vz-temuan">
      <span className="vz-temuan-no">Temuan {no}</span>
      <h2>{judul}</h2>
      {children}
      {artinya && (
        <div className="vz-artinya">
          {artinya.map(([siapa, isi]) => (
            <div key={siapa}>
              <strong>Bagi {siapa}</strong>
              {isi}
            </div>
          ))}
        </div>
      )}
    </article>
  )
}

const gabungBobot = (rows) => {
  const n = rows.reduce((s, r) => s + r.n, 0)
  return n ? rows.reduce((s, r) => s + r.rata_perubahan_7h_pct * r.n, 0) / n : null
}

// ---------------- 1. hari besar ----------------
function TemuanHariBesar({ rows }) {
  const per = new Map()
  for (const r of rows) {
    if (r.rata_perubahan_7h_pct == null) continue
    const k = per.get(r.kategori) || { kategori: r.kategori, ya: [], tidak: [] }
    ;(r.menjelang_hari_besar ? k.ya : k.tidak).push(r)
    per.set(r.kategori, k)
  }
  const data = [...per.values()]
    .map((k) => ({ kategori: k.kategori, menjelang: gabungBobot(k.ya), biasa: gabungBobot(k.tidak) }))
    .filter((d) => d.menjelang != null && d.biasa != null)
    .map((d) => ({ ...d, menjelang: Math.round(d.menjelang * 100) / 100, biasa: Math.round(d.biasa * 100) / 100 }))
    .sort((a, b) => b.menjelang - b.biasa - (a.menjelang - a.biasa))
  if (!data.length) return null
  const top = data[0]
  const kali = top.biasa > 0.05 ? top.menjelang / top.biasa : null
  const judul = `Menjelang hari besar, harga ${top.kategori.toLowerCase()} naik rata-rata ${fmtPct(top.menjelang)} dalam sepekan${
    kali && kali > 1.5 ? `, sekitar ${fmtAngka(kali, 1)} kali kenaikan pada hari biasa (${fmtPct(top.biasa)})` : `, dibanding ${fmtPct(top.biasa)} pada hari biasa`
  }`
  return (
    <Temuan
      no={1}
      judul={judul}
      artinya={[
        ['konsumen', `Belanja ${top.kategori.toLowerCase()} untuk keperluan hari besar lebih dari seminggu sebelumnya, sebelum harga mulai naik.`],
        ['pedagang', `Permintaan dan harga ${top.kategori.toLowerCase()} paling tinggi pada pekan menjelang hari besar; tambah stok sebelum pekan itu.`],
        ['pemerintah', `Operasi pasar dan pemantauan stok paling berdampak bila dimulai 1 sampai 2 minggu sebelum hari besar, terutama untuk ${top.kategori.toLowerCase()}.`],
      ]}
    >
      <div className="grafik" style={{ height: tinggiBatang(data.length * 2) }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ top: 4, right: 56, left: 8, bottom: 0 }} barGap={2}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--garis, #e5e7eb)" horizontal={false} />
            <XAxis type="number" domain={domainBerlabel()} tickFormatter={(v) => fmtPct(v, { digit: 0 })} tick={{ fontSize: 11 }} />
            <YAxis type="category" dataKey="kategori" width={140} tick={{ fontSize: 12 }} />
            <ReferenceLine x={0} stroke="#6b7280" />
            <Tooltip formatter={(v, n) => [fmtPct(v, { digit: 2 }), n]} />
            <Legend />
            <Bar dataKey="biasa" name="Hari biasa" fill={WARNA.abu} radius={4} isAnimationActive={false}>
              <LabelList dataKey="biasa" position="right" formatter={(v) => fmtPct(v)} style={{ fontSize: 11, fill: '#374151' }} />
            </Bar>
            <Bar dataKey="menjelang" name="1–7 hari menjelang hari besar" fill={WARNA.oranye} radius={4} isAnimationActive={false}>
              <LabelList dataKey="menjelang" position="right" formatter={(v) => fmtPct(v)} style={{ fontSize: 11, fill: '#374151' }} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="catatan">
        Rata-rata perubahan harga 7 hari di semua pasar, dikelompokkan menurut kategori komoditas. Hari besar: Tahun Baru, Imlek, awal Ramadan, Idulfitri,
        Iduladha, Natal (2024–2026).
      </p>
    </Temuan>
  )
}

// ---------------- 2. volatilitas ----------------
function TemuanVolatilitas({ rows }) {
  const data = rows
    .filter((r) => r.rata_abs_pct != null)
    .map((r) => ({ ...r, nilai: Math.round(r.rata_abs_pct * 10) / 10 }))
    .sort((a, b) => b.nilai - a.nilai)
  if (data.length < 2) return null
  const top = data[0]
  const bawah = data[data.length - 1]
  const kali = bawah.nilai > 0 ? top.nilai / bawah.nilai : null
  const judul = `${top.nama} paling bergejolak: harganya berubah rata-rata ${fmtAngka(top.nilai, 1)}% setiap minggu${
    kali ? `, ${fmtAngka(kali, 0)} kali ${bawah.nama.toLowerCase()}` : ''
  }`
  const bergejolak = data.filter((d) => d.nilai >= 3).map((d) => d.nama.toLowerCase())
  return (
    <Temuan
      no={2}
      judul={judul}
      artinya={[
        ['konsumen', `Harga ${top.nama.toLowerCase()} minggu ini bukan patokan untuk minggu depan; harga ${bawah.nama.toLowerCase()} jauh lebih stabil.`],
        ['pedagang', `Risiko rugi stok paling besar pada ${bergejolak.join(', ') || top.nama.toLowerCase()}; beli dalam jumlah lebih kecil dan lebih sering.`],
        ['pemerintah', `Pantau harian ${bergejolak.join(', ') || top.nama.toLowerCase()}; komoditas yang stabil cukup dipantau mingguan.`],
      ]}
    >
      <div className="grafik" style={{ height: tinggiBatang(data.length) }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ top: 4, right: 56, left: 8, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--garis, #e5e7eb)" horizontal={false} />
            <XAxis type="number" tickFormatter={(v) => `${v}%`} tick={{ fontSize: 11 }} />
            <YAxis type="category" dataKey="nama" width={140} tick={{ fontSize: 12 }} />
            <Tooltip
              formatter={(v, _n, it) => [
                `${fmtAngka(v, 1)}% per minggu (naik terbesar ${fmtPct(it.payload.naik_maks_pct, { digit: 0 })}, turun terbesar ${fmtPct(it.payload.turun_maks_pct, { digit: 0 })})`,
                'Rata-rata perubahan mingguan',
              ]}
            />
            <Bar dataKey="nilai" radius={4} isAnimationActive={false}>
              {data.map((d) => (
                <Cell key={d.komoditas} fill={d.nilai >= 3 ? WARNA.oranye : WARNA.biru} />
              ))}
              <LabelList dataKey="nilai" position="right" formatter={(v) => `${fmtAngka(v, 1)}%`} style={{ fontSize: 11, fill: '#374151' }} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="catatan">
        Rata-rata besarnya perubahan harga median kota dari minggu ke minggu (naik maupun turun). Oranye = berubah 3% atau lebih per minggu.
      </p>
    </Temuan>
  )
}

// ---------------- 3. disparitas antarpasar ----------------
function TemuanDisparitas({ rows }) {
  const data = rows
    .filter((r) => r.rata_periode != null)
    .map((r) => ({ ...r, nilai: Math.round(r.rata_periode * 10) / 10, catatan: CATATAN_DATA[r.komoditas] }))
    .sort((a, b) => b.nilai - a.nilai)
  const layak = data.filter((d) => !d.catatan || d.komoditas === 'telur_ayam_ras')
  if (!layak.length) return null
  const top = layak[0]
  const judul = `Pada hari yang sama, harga ${top.nama.toLowerCase()} di pasar termahal rata-rata ${fmtAngka(top.nilai, 0)}% lebih tinggi daripada di pasar termurah`
  return (
    <Temuan
      no={3}
      judul={judul}
      artinya={[
        ['konsumen', `Membandingkan beberapa pasar sebelum membeli ${top.nama.toLowerCase()} bisa menghemat cukup besar; lihat halaman Perbandingan.`],
        ['pedagang', 'Selisih antarpasar yang lebar membuka peluang mengambil pasokan dari pasar yang lebih murah.'],
        ['pemerintah', 'Selisih yang terus lebar menandakan pasokan belum merata antarwilayah; telusuri pasar yang konsisten lebih mahal (temuan 4).'],
      ]}
    >
      <div className="grafik" style={{ height: tinggiBatang(data.length) }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ top: 4, right: 56, left: 8, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--garis, #e5e7eb)" horizontal={false} />
            <XAxis type="number" tickFormatter={(v) => `${v}%`} tick={{ fontSize: 11 }} />
            <YAxis type="category" dataKey="nama" width={140} tick={{ fontSize: 12 }} />
            <Tooltip
              formatter={(v, _n, it) => [
                `${fmtAngka(v, 1)}% rata-rata, pernah ${fmtAngka(it.payload.maks_periode, 0)}%${it.payload.catatan ? ` · catatan: ${it.payload.catatan}` : ''}`,
                'Selisih termahal–termurah',
              ]}
            />
            <Bar dataKey="nilai" radius={4} isAnimationActive={false}>
              {data.map((d) => (
                <Cell key={d.komoditas} fill={d.catatan && d.komoditas !== 'telur_ayam_ras' ? WARNA.abu : WARNA.biru} />
              ))}
              <LabelList dataKey="nilai" position="right" formatter={(v) => `${fmtAngka(v, 0)}%`} style={{ fontSize: 11, fill: '#374151' }} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="catatan">
        Selisih harga termahal dan termurah antarpasar pada hari yang sama, dibagi median, dirata-ratakan sepanjang periode (hanya hari dengan minimal 3
        pasar melapor). Batang abu: {Object.entries(CATATAN_DATA).filter(([k]) => k !== 'telur_ayam_ras').map(([k, v]) => `${k.replace(/_/g, ' ')} (${v})`).join('; ')}.
      </p>
    </Temuan>
  )
}

// ---------------- 4. pasar termahal / termurah ----------------
function TemuanPasar({ pasar }) {
  const data = pasar
    .filter((p) => p.selisih_pct != null)
    .map((p) => ({ ...p, nilai: Math.round(p.selisih_pct * 10) / 10, label: p.nama_pasar }))
    .sort((a, b) => b.nilai - a.nilai)
  const urutLaporan = data.map((d) => d.laporan).sort((a, b) => a - b)
  const medianLaporan = urutLaporan[Math.floor(urutLaporan.length / 2)] || 0
  const cukup = (d) => d.komoditas >= 5 && d.laporan >= medianLaporan / 2
  const layak = data.filter(cukup)
  if (layak.length < 2) return null
  const mahal = layak[0]
  const murah = layak[layak.length - 1]
  const judul = `${mahal.nama_pasar} (${mahal.kecamatan}) rata-rata ${fmtAngka(mahal.nilai, 1)}% di atas median kota, sedangkan ${murah.nama_pasar} (${murah.kecamatan}) ${fmtAngka(Math.abs(murah.nilai), 1)}% di bawahnya`
  return (
    <Temuan
      no={4}
      judul={judul}
      artinya={[
        ['konsumen', `Untuk belanja rutin, ${murah.nama_pasar} cenderung lebih murah daripada pasar lain di Medan.`],
        ['pedagang', `Harga di ${mahal.nama_pasar} konsisten lebih tinggi; pedagang di pasar lain punya ruang bersaing harga.`],
        ['pemerintah', `Periksa rantai pasok dan biaya distribusi ke ${mahal.nama_pasar}; selisih yang konsisten bukan kebetulan harian.`],
      ]}
    >
      <div className="grafik" style={{ height: tinggiBatang(data.length) }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ top: 4, right: 56, left: 8, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--garis, #e5e7eb)" horizontal={false} />
            <XAxis type="number" domain={domainBerlabel()} tickFormatter={(v) => fmtPct(v, { digit: 0 })} tick={{ fontSize: 11 }} />
            <YAxis type="category" dataKey="label" width={160} tick={{ fontSize: 11 }} />
            <ReferenceLine x={0} stroke="#6b7280" />
            <Tooltip
              formatter={(v, _n, it) => [
                `${fmtPct(v)} · ${it.payload.kecamatan} · ${it.payload.komoditas} komoditas · ${fmtAngka(it.payload.laporan)} laporan`,
                'Selisih terhadap median kota',
              ]}
            />
            <Bar dataKey="nilai" radius={4} isAnimationActive={false}>
              {data.map((d) => (
                <Cell key={d.label} fill={!cukup(d) ? WARNA.abu : d.nilai > 0 ? WARNA.oranye : WARNA.biru} />
              ))}
              <LabelList dataKey="nilai" position="right" formatter={(v) => fmtPct(v)} style={{ fontSize: 11, fill: '#374151' }} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="catatan">
        Rata-rata selisih harga tiap pasar terhadap median harga semua pasar pada hari dan komoditas yang sama, untuk semua komoditas yang dilaporkan
        pasar itu. Abu = pasar dengan data terbatas (kurang dari 5 komoditas atau kurang dari separuh jumlah laporan pasar pada umumnya); tetap
        ditampilkan, tetapi tidak dipakai untuk judul.
      </p>
    </Temuan>
  )
}

// ---------------- 5. model vs baseline ----------------
function TemuanModel({ deret, namaKom }) {
  const h7 = deret.filter((e) => e.horizon === 7)
  if (!h7.length) return null
  const menang = h7.filter((e) => e.mengalahkan_baseline).length
  const per = new Map()
  for (const e of h7) {
    const k = per.get(e.komoditas) || { komoditas: e.komoditas, nama: namaKom(e.komoditas), m: [], b: [] }
    k.m.push(e.mape_model)
    k.b.push(e.mape_baseline)
    per.set(e.komoditas, k)
  }
  const rata = (xs) => xs.reduce((s, x) => s + x, 0) / xs.length
  const data = [...per.values()]
    .map((k) => ({ nama: k.nama, model: Math.round(rata(k.m) * 100) / 100, baseline: Math.round(rata(k.b) * 100) / 100 }))
    .sort((a, b) => b.baseline - a.baseline)
  const bagian = menang / h7.length
  const judul =
    bagian >= 0.5
      ? `Model prediksi lebih akurat daripada tebakan "harga tetap" pada ${menang} dari ${h7.length} deret untuk 7 hari ke depan`
      : `Harga bahan pokok sulit ditebak: untuk 7 hari ke depan, model hanya mengalahkan tebakan "harga tetap" pada ${menang} dari ${h7.length} deret`
  return (
    <Temuan
      no={5}
      judul={judul}
      artinya={[
        ['konsumen', 'Gunakan rentang prediksi di halaman Prediksi sebagai gambaran kisaran harga, bukan janji harga.'],
        ['pedagang', 'Untuk komoditas yang stabil, harga hari ini sudah menjadi perkiraan yang baik untuk minggu depan.'],
        ['pemerintah', 'Status Waspada/Lonjakan lebih andal dibaca bersama perubahan harga aktual, bukan dari angka prediksi tunggal.'],
      ]}
    >
      <div className="grafik" style={{ height: tinggiBatang(data.length * 2) }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ top: 4, right: 56, left: 8, bottom: 0 }} barGap={2}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--garis, #e5e7eb)" horizontal={false} />
            <XAxis type="number" tickFormatter={(v) => `${v}%`} tick={{ fontSize: 11 }} />
            <YAxis type="category" dataKey="nama" width={140} tick={{ fontSize: 12 }} />
            <Tooltip formatter={(v, n) => [`${fmtAngka(v, 2)}%`, n]} />
            <Legend />
            <Bar dataKey="baseline" name='Tebakan "harga tetap" (baseline)' fill={WARNA.abu} radius={4} isAnimationActive={false}>
              <LabelList dataKey="baseline" position="right" formatter={(v) => `${fmtAngka(v, 1)}%`} style={{ fontSize: 11, fill: '#374151' }} />
            </Bar>
            <Bar dataKey="model" name="Model" fill={WARNA.biru} radius={4} isAnimationActive={false}>
              <LabelList dataKey="model" position="right" formatter={(v) => `${fmtAngka(v, 1)}%`} style={{ fontSize: 11, fill: '#374151' }} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="catatan">
        MAPE (rata-rata galat persen, makin kecil makin baik) pada uji walk-forward horizon 7 hari, dirata-ratakan per komoditas. Rincian per deret ada
        di halaman <Link to="/prediksi">Prediksi</Link>.
      </p>
    </Temuan>
  )
}

export default function Cerita() {
  const { ref, versiModel } = useApp()
  const stat = useMuat(() => api.analitik.statistik(), `stat-cerita|${versiModel}`)
  const wil = useMuat(() => api.analitik.wilayah(), `wil-cerita|${versiModel}`)
  const ev = useMuat(() => api.evaluasi(), `ev-cerita|${versiModel}`)
  const kpi = useMuat(() => api.analitik.kpi(), `kpi|${versiModel}`)
  const namaKom = (kode) => ref.komoditas.find((k) => k.kode === kode)?.nama ?? kode

  const galat = stat.galat || wil.galat
  return (
    <>
      <div className="bar-judul">
        <h1>Cerita data: apa yang terjadi pada harga bahan pokok di Medan?</h1>
      </div>
      <p className="catatan" style={{ marginTop: 0 }}>
        Lima temuan dari data harga harian SIMPANG Pemko Medan dan SP2KP Kemendag{kpi.data?.tanggal ? ` sampai ${labelTanggal(kpi.data.tanggal)}` : ''}. Judul tiap
        grafik dihitung otomatis dari data terbaru. Untuk menelusuri sendiri, buka <Link to="/analisis">Analisis</Link>.
      </p>
      {galat && <Galat pesan={galat.message} detail={galat.detail} />}
      {!galat && (!stat.data || !wil.data) && <Memuat />}
      {stat.data && wil.data && (
        <div className="vz-cerita">
          <TemuanHariBesar rows={stat.data.hari_besar} />
          <TemuanVolatilitas rows={stat.data.volatilitas} />
          <TemuanDisparitas rows={stat.data.disparitas} />
          <TemuanPasar pasar={wil.data.pasar} />
          {ev.data?.deret?.length ? (
            <TemuanModel deret={ev.data.deret} namaKom={namaKom} />
          ) : (
            <article className="panel vz-temuan">
              <span className="vz-temuan-no">Temuan 5</span>
              <p className="catatan">Hasil evaluasi model belum tersedia. Tunggu pelatihan model selesai.</p>
            </article>
          )}
        </div>
      )}
    </>
  )
}
