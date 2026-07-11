"use client";

export interface Filters {
  maxPrice: number;
  maxKm: number;
}

export default function FilterPanel({
  filters,
  onChange,
  priceBounds,
}: {
  filters: Filters;
  onChange: (f: Filters) => void;
  priceBounds: { min: number; max: number };
}) {
  return (
    <div>
      <div className="section-title">Filters</div>
      <div className="field">
        <label>Max price: ${filters.maxPrice}/mo</label>
        <input
          type="range"
          min={priceBounds.min}
          max={priceBounds.max}
          step={50}
          value={filters.maxPrice}
          onChange={(e) => onChange({ ...filters, maxPrice: Number(e.target.value) })}
        />
      </div>
      <div className="field">
        <label>Max distance from center: {filters.maxKm} km</label>
        <input
          type="range"
          min={1}
          max={20}
          step={1}
          value={filters.maxKm}
          onChange={(e) => onChange({ ...filters, maxKm: Number(e.target.value) })}
        />
      </div>
    </div>
  );
}
