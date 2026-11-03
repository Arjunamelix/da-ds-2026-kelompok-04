import { Tooltip, useTooltip } from './Tooltip.jsx'
import './viz.css'

// Peta panas baris x kolom (HTML grid). Setiap sel adalah tombol: hover = tooltip, klik = filter silang.
//   baris:  [{ kunci, label }]
//   kolom:  [{ kunci, label }]
//   nilai:  (kunciBaris, kunciKolom) => number | null
//   warna:  (v) => hex latar
//   isiTooltip: (barisObj, kolomObj, v) => node
//   labelSel: (v) => string | null   teks di dalam sel (opsional)
export default function Heatmap({
  baris, kolom, nilai, warna, warnaTeks, isiTooltip, labelSel, onKlikSel, onKlikBaris,
  barisAktif, kolomAktif, lebarSel = 30, lebarLabel = 150, labelKolom = (k) => k.label, judulAria, kolomTegak = false,
}) {
  const { tip, tampil, sembunyi } = useTooltip()
  const template = `${lebarLabel}px repeat(${kolom.length}, ${lebarSel}px)`

  return (
    <div className="vz-gulir">
      <div className="vz-heat" style={{ gridTemplateColumns: template }} role="grid" aria-label={judulAria}>
        <div />
        {kolom.map((k, i) => (
          <div key={k.kunci} className={'vz-heat-kepala' + (kolomTegak ? ' tegak' : '')} role="columnheader" title={k.label}>
            {labelKolom(k, i)}
          </div>
        ))}
        {baris.map((b) => (
          <Baris
            key={b.kunci}
            b={b}
            kolom={kolom}
            nilai={nilai}
            warna={warna}
            warnaTeks={warnaTeks}
            isiTooltip={isiTooltip}
            labelSel={labelSel}
            onKlikSel={onKlikSel}
            onKlikBaris={onKlikBaris}
            aktif={barisAktif === b.kunci}
            kolomAktif={kolomAktif}
            tampil={tampil}
            sembunyi={sembunyi}
          />
        ))}
      </div>
      <Tooltip tip={tip} />
    </div>
  )
}

function Baris({ b, kolom, nilai, warna, warnaTeks, isiTooltip, labelSel, onKlikSel, onKlikBaris, aktif, kolomAktif, tampil, sembunyi }) {
  return (
    <>
      <button
        type="button"
        className={'vz-heat-baris' + (aktif ? ' aktif' : '')}
        onClick={onKlikBaris ? () => onKlikBaris(b) : undefined}
        aria-pressed={aktif}
        role="rowheader"
      >
        {b.label}
      </button>
      {kolom.map((k) => {
        const v = nilai(b.kunci, k.kunci)
        if (v == null) {
          return <div key={k.kunci} className="vz-sel kosong" title={`${b.label} · ${k.label}: tidak ada data`} />
        }
        const latar = warna(v)
        const isi = isiTooltip(b, k, v)
        return (
          <button
            key={k.kunci}
            type="button"
            className={'vz-sel' + (aktif && kolomAktif === k.kunci ? ' aktif' : '')}
            style={{ background: latar, color: warnaTeks ? warnaTeks(latar) : '#1f2937' }}
            onMouseMove={(e) => tampil(e, isi)}
            onMouseLeave={sembunyi}
            onFocus={(e) => tampil(e, isi)}
            onBlur={sembunyi}
            onClick={onKlikSel ? () => onKlikSel(b, k, v) : undefined}
            aria-label={`${b.label}, ${k.label}`}
          >
            {labelSel ? labelSel(v) : ''}
          </button>
        )
      })}
    </>
  )
}

// Legenda skala divergen.
export function LegendaDivergen({ kiri, tengah, kanan, warnaKiri, warnaTengah, warnaKanan }) {
  return (
    <div className="vz-legenda">
      <span>{kiri}</span>
      <span className="vz-legenda-gradien" style={{ background: `linear-gradient(90deg, ${warnaKiri}, ${warnaTengah}, ${warnaKanan})` }} />
      <span>{kanan}</span>
      {tengah && <span>· tengah = {tengah}</span>}
      <span>
        <span className="vz-legenda-kotak" style={{ background: 'repeating-linear-gradient(45deg,#f3f4f6,#f3f4f6 3px,#e5e7eb 3px,#e5e7eb 5px)' }} />
        tidak ada data
      </span>
    </div>
  )
}
