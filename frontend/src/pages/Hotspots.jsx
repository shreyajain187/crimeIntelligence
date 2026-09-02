import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, Circle, Tooltip } from 'react-leaflet'
import api from '../api/client'
import { PageHeader, Panel, LoadingState, ErrorState } from '../components/Panel'

const KARNATAKA_CENTER = [14.5, 75.7]

export default function Hotspots() {
  const [hotspots, setHotspots] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.hotspots({ limit: 500 }).then(setHotspots).catch((e) => setError(e.message))
  }, [])

  if (error) return <ErrorState message={error} />
  if (!hotspots) return <LoadingState label="Loading DBSCAN hotspot clusters…" />

  return (
    <div>
      <PageHeader
        eyebrow="HOTSPOTS"
        title="Geographic Crime Hotspots"
        description="DBSCAN clusters over real geocoded incidents (haversine distance, eps≈0.75km, min 15 incidents). Cluster −1 (noise) is excluded from this list."
      />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 px-8 py-6">
        <Panel title="Hotspot map" subtitle={`${hotspots.length} clusters, sized by incident count`}>
          <div style={{ height: 460 }}>
            <MapContainer center={KARNATAKA_CENTER} zoom={7} style={{ height: '100%', width: '100%' }}>
              <TileLayer
                url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}"
                attribution='Tiles &copy; Esri — Esri, HERE, Garmin, FAO, NOAA, USGS'
              />
              {hotspots.map((h) => (
                <Circle
                  key={h.cluster_id}
                  center={[h.centroid_lat, h.centroid_lon]}
                  radius={Math.min(Math.sqrt(h.incident_count) * 80, 10000)}
                  pathOptions={{ color: '#d6552e', fillColor: '#d6552e', fillOpacity: 0.25, weight: 1 }}
                >
                  <Tooltip>{h.district}: {h.incident_count.toLocaleString()} incidents · {h.dominant_crime_type}</Tooltip>
                </Circle>
              ))}
            </MapContainer>
          </div>
        </Panel>

        <Panel title="Hotspot table" subtitle="Ranked by incident count">
          <div className="max-h-[460px] overflow-y-auto">
            <table className="w-full text-[12px]">
              <thead className="sticky top-0 bg-surface-raised">
                <tr className="text-left text-ink-dim">
                  <th className="py-2 px-2">District</th>
                  <th className="py-2 px-2 text-right">Incidents</th>
                  <th className="py-2 px-2 text-right">Density/km²</th>
                  <th className="py-2 px-2">Dominant type</th>
                </tr>
              </thead>
              <tbody>
                {hotspots.slice(0, 100).map((h) => (
                  <tr key={h.cluster_id} className="border-t border-line hover:bg-surface-raised/50">
                    <td className="py-1.5 px-2 text-ink-muted">{h.district}</td>
                    <td className="py-1.5 px-2 text-right font-mono">{h.incident_count.toLocaleString()}</td>
                    <td className="py-1.5 px-2 text-right font-mono">{h.density_per_km2.toFixed(1)}</td>
                    <td className="py-1.5 px-2 text-ink-muted truncate max-w-[160px]">{h.dominant_crime_type}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      </div>
    </div>
  )
}
