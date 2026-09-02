import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup, Circle } from 'react-leaflet'
import api from '../api/client'
import { PageHeader, LoadingState, ErrorState } from '../components/Panel'

const KARNATAKA_CENTER = [14.5, 75.7]

export default function CrimeMap() {
  const [districts, setDistricts] = useState([])
  const [crimeGroups, setCrimeGroups] = useState([])
  const [district, setDistrict] = useState('')
  const [crimeGroup, setCrimeGroup] = useState('')
  const [showHotspots, setShowHotspots] = useState(true)
  const [points, setPoints] = useState(null)
  const [hotspots, setHotspots] = useState([])
  const [error, setError] = useState(null)

  useEffect(() => {
    api.districts().then(setDistricts).catch(() => {})
    api.crimeGroups().then(setCrimeGroups).catch(() => {})
    api.hotspots({ limit: 300 }).then(setHotspots).catch(() => {})
  }, [])

  useEffect(() => {
    const params = { limit: 4000 }
    if (district) params.district = district
    if (crimeGroup) params.crime_group = crimeGroup
    api.crimesForMap(params).then(setPoints).catch((e) => setError(e.message))
  }, [district, crimeGroup])

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        eyebrow="CRIME MAP"
        title="Interactive Incident Map"
        description="Point-level incidents with real coordinates only — no location is ever fabricated for a record without one."
      />
      <div className="px-8 py-4 flex flex-wrap gap-3 items-center border-b border-line">
        <select
          value={district}
          onChange={(e) => setDistrict(e.target.value)}
          className="bg-surface-raised border border-line text-[12.5px] px-3 py-1.5 text-ink"
        >
          <option value="">All districts</option>
          {districts.map((d) => <option key={d} value={d}>{d}</option>)}
        </select>
        <select
          value={crimeGroup}
          onChange={(e) => setCrimeGroup(e.target.value)}
          className="bg-surface-raised border border-line text-[12.5px] px-3 py-1.5 text-ink"
        >
          <option value="">All crime groups</option>
          {crimeGroups.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <label className="flex items-center gap-2 text-[12.5px] text-ink-muted">
          <input type="checkbox" checked={showHotspots} onChange={(e) => setShowHotspots(e.target.checked)} />
          Show hotspot overlays
        </label>
        {points && <span className="text-[11.5px] font-mono text-ink-dim ml-auto">{points.length.toLocaleString()} points shown (capped)</span>}
      </div>

      <div className="flex-1 relative">
        {error && <div className="absolute inset-0 z-[500] bg-void/90"><ErrorState message={error} /></div>}
        {!points && !error && <LoadingState label="Loading incident points…" />}
        {points && (
          <MapContainer center={KARNATAKA_CENTER} zoom={7} style={{ height: '100%', width: '100%', background: '#14161b' }}>
            <TileLayer
              url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}"
              attribution='Tiles &copy; Esri — Esri, HERE, Garmin, FAO, NOAA, USGS'
            />
            {showHotspots && hotspots.map((h) => (
              <Circle
                key={h.cluster_id}
                center={[h.centroid_lat, h.centroid_lon]}
                radius={Math.min(Math.sqrt(h.incident_count) * 60, 8000)}
                pathOptions={{ color: '#d6552e', fillColor: '#d6552e', fillOpacity: 0.12, weight: 1 }}
              />
            ))}
            {points.map((p) => (
              <CircleMarker
                key={p.crime_id}
                center={[p.latitude, p.longitude]}
                radius={3}
                pathOptions={{ color: '#6e93b0', fillColor: '#6e93b0', fillOpacity: 0.7, weight: 0 }}
              >
                <Popup>
                  <div className="text-[12px]">
                    <strong>{p.crime_type}</strong><br />
                    {p.crime_group}<br />
                    {p.location}<br />
                    {new Date(p.timestamp).toLocaleDateString()}
                  </div>
                </Popup>
              </CircleMarker>
            ))}
          </MapContainer>
        )}
      </div>
    </div>
  )
}
