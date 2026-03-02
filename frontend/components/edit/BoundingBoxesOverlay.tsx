'use client';

interface Polygon {
  bbox: number[];
  class: 'live' | 'dead';
  confidence: number;
}

interface BoundingBoxesOverlayProps {
  polygons: Polygon[];
  isEditMode: boolean;
  editingPolygonIndex: number | null;
  onPolygonClick: (index: number) => void;
  onPolygonHover: (index: number | null) => void;
}

function getPolygonBounds(coords: number[][]) {
  if (!coords || coords.length === 0) {
    return null;
  }

  const xs = coords.map((coord) => coord[0]);
  const ys = coords.map((coord) => coord[1]);
  return {
    minX: Math.min(...xs),
    minY: Math.min(...ys),
    maxX: Math.max(...xs),
    maxY: Math.max(...ys),
  };
}

function convertBboxToCoords(bbox: number[]) {
  if (!Array.isArray(bbox) || bbox.length !== 4) {
    return [];
  }

  const [x1, y1, x2, y2] = bbox;
  return [
    [x1, y1],
    [x2, y1],
    [x2, y2],
    [x1, y2],
  ];
}

export default function BoundingBoxesOverlay({
  polygons,
  isEditMode,
  editingPolygonIndex,
  onPolygonClick,
  onPolygonHover,
}: BoundingBoxesOverlayProps) {
  if (!polygons || polygons.length === 0) return null;

  return (
    <svg
      className="absolute top-0 left-0 w-full h-full pointer-events-none rounded"
    >
      {polygons.map((polygon: Polygon, index: number) => {
        const coords = convertBboxToCoords(polygon.bbox);
        const bounds = getPolygonBounds(coords);

        if (!bounds || coords.length === 0) {
          return null;
        }

        const pathData = coords
          .map((coord: number[], i: number) => 
            `${i === 0 ? 'M' : 'L'} ${coord[0]} ${coord[1]}`
          )
          .join(' ') + ' Z';

        // Color based on class
        const strokeColor = polygon.class === 'live' 
          ? '#22c55e' // green-500
          : '#ef4444'; // red-500
        
        const fillColor = polygon.class === 'live'
          ? 'rgba(34, 197, 94, 0.1)' 
          : 'rgba(239, 68, 68, 0.1)';

        return (
          <g 
            key={index}
            style={{ cursor: isEditMode ? 'pointer' : 'default' }}
            className={isEditMode ? "pointer-events-auto" : "pointer-events-none"}
          >
            {/* bounding box */}
            <path
              d={pathData}
              fill={editingPolygonIndex === index ? fillColor.replace('0.1', '0.3') : fillColor}
              stroke={strokeColor}
              strokeWidth={editingPolygonIndex === index ? "3" : "2"}
              className={`transition-opacity ${isEditMode ? "hover:opacity-80 pointer-events-auto" : "pointer-events-none"}`}
              onMouseEnter={() => isEditMode && onPolygonHover(index)}
              onMouseLeave={() => onPolygonHover(null)}
              onClick={() => {
                if (isEditMode) {
                  onPolygonClick(index);
                }
              }}
            />

            {/* label w/ confidence */}
            {(() => {
              const labelText = `${polygon.class} ${(polygon.confidence * 100).toFixed(0)}%`;
              const labelX = bounds.minX;
              const labelY = bounds.minY - 5;

              const textWidth = labelText.length * 6;
              const textHeight = 14;
              const padding = 4;
              const rectWidth = textWidth + padding * 2;
              const rectHeight = textHeight + padding * 2;
              
              return (
                <g
                  onClick={(e) => {
                    e.stopPropagation();
                    if (isEditMode) {
                      onPolygonClick(index);
                    }
                  }}
                  style={{ cursor: isEditMode ? 'pointer' : 'default' }}
                  className={isEditMode ? "hover:opacity-80 pointer-events-auto" : "pointer-events-none"}
                >
                  {/* label box */}
                  <rect
                    x={labelX - padding}
                    y={labelY - textHeight - padding}
                    width={rectWidth + (polygon.class === 'dead' ? 7 : 0)}
                    height={rectHeight}
                    fill="white"
                    stroke="black"
                    strokeWidth="1.5"
                    rx="2"
                    className={isEditMode ? "hover:opacity-80 transition-opacity" : ""}
                  />
                  {/* text */}
                  <text
                    x={labelX}
                    y={labelY - padding / 2}
                    fill="black"
                    fontSize="12"
                    fontWeight="bold"
                  >
                    {labelText}
                  </text>
                </g>
              );
            })()}
          </g>
        );
      })}
    </svg>
  );
}
