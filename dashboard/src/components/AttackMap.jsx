import React, { useMemo } from "react";
import {
    ComposableMap,
    Geographies,
    Geography,
    Marker,
    ZoomableGroup
} from "react-simple-maps";

const geoUrl =
    "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json";

const AttackMap = ({ attacks }) => {
    // Memoize unique attacks to avoid flickering if possible, though React handles this well
    const markers = useMemo(() => {
        return attacks.map(attack => ({
            name: attack.ip,
            coordinates: attack.coordinates,
            type: attack.type,
            id: attack.id
        }));
    }, [attacks]);

    return (
        <div style={{ width: "100%", height: "400px", background: "#0f0f13", borderRadius: "12px", overflow: "hidden", border: "1px solid #2a2a2a" }}>
            <ComposableMap
                projection="geoMercator"
                projectionConfig={{
                    scale: 100
                }}
                style={{ width: "100%", height: "100%" }}
            >
                <ZoomableGroup center={[0, 20]} zoom={1}>
                    <Geographies geography={geoUrl}>
                        {({ geographies }) =>
                            geographies.map((geo) => (
                                <Geography
                                    key={geo.rsmKey}
                                    geography={geo}
                                    fill="#1a1a1a"
                                    stroke="#333"
                                    strokeWidth={0.5}
                                    style={{
                                        default: { fill: "#1a1a1a", outline: "none" },
                                        hover: { fill: "#2a2a2a", outline: "none" },
                                        pressed: { fill: "#1a1a1a", outline: "none" },
                                    }}
                                />
                            ))
                        }
                    </Geographies>
                    {markers.map(({ name, coordinates, type, id }) => (
                        <Marker key={id} coordinates={coordinates}>
                            <circle r={4} fill={type === "BLOCK" ? "#ef4444" : "#eab308"} stroke="#000" strokeWidth={1} style={{ animation: "pulse 1s infinite" }} />
                        </Marker>
                    ))}
                </ZoomableGroup>
            </ComposableMap>

            {/* Legend / Overlay */}
            <div style={{ position: "absolute", bottom: "20px", left: "20px", background: "rgba(0,0,0,0.7)", padding: "10px", borderRadius: "8px", border: "1px solid #333", fontSize: "12px", color: "#ccc" }}>
                <div style={{ display: "flex", alignItems: "center", marginBottom: "4px" }}>
                    <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#ef4444", marginRight: "6px" }}></div>
                    Blocked
                </div>
                <div style={{ display: "flex", alignItems: "center" }}>
                    <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#eab308", marginRight: "6px" }}></div>
                    Challenge / Mitigated
                </div>
            </div>

            <style>{`
        @keyframes pulse {
            0% { transform: scale(1); opacity: 1; }
            50% { transform: scale(1.5); opacity: 0.7; }
            100% { transform: scale(1); opacity: 1; }
        }
      `}</style>
        </div>
    );
};

export default AttackMap;
