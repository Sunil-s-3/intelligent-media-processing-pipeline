import { AnalysisCard, ResultRow, StatusBadge, ConfidenceBar } from './AnalysisCard'

const PATTERN_LABEL = {
  standard: 'Standard (e.g. KA01AB1234)',
  bharat_series: 'Bharat series (e.g. 22BH1234AA)',
}

export default function VehicleNumberCard({ vehicleNumber }) {
  if (!vehicleNumber) return null
  return (
    <AnalysisCard title="Vehicle Number">
      <ResultRow
        label="Format valid"
        value={
          <StatusBadge
            value={vehicleNumber.format_valid}
            trueLabel="Valid format"
            falseLabel="No match"
            trueIsGood
          />
        }
      />
      <ResultRow
        label="Matched value"
        value={vehicleNumber.matched_value ?? 'None'}
        mono
      />
      <ResultRow
        label="Pattern"
        value={
          vehicleNumber.matched_pattern
            ? PATTERN_LABEL[vehicleNumber.matched_pattern] ?? vehicleNumber.matched_pattern
            : '—'
        }
      />
      <ResultRow
        label="Normalized text"
        value={vehicleNumber.normalized_text ?? '—'}
        mono
      />
      {vehicleNumber.reason && (
        <p className="text-[11px] text-gray-500 pt-1 italic">{vehicleNumber.reason}</p>
      )}
      <ConfidenceBar value={vehicleNumber.confidence} />
      <p className="text-[10px] text-gray-400 pt-1">
        Format validation only — does not verify that the plate is genuine or the OCR is correct.
      </p>
    </AnalysisCard>
  )
}
