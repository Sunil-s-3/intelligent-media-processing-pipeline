import { AnalysisCard, ResultRow, StatusBadge, ConfidenceBar } from './AnalysisCard'

export default function ScreenshotCard({ screenshot }) {
  if (!screenshot) return null
  return (
    <AnalysisCard title="Screenshot / Editing Heuristic">
      <ResultRow
        label="Detected"
        value={
          <StatusBadge
            value={screenshot.detected ?? screenshot.issue}
            trueLabel="Possible screenshot"
            falseLabel="No signal"
          />
        }
      />
      <ResultRow
        label="Editing indicators"
        value={
          <StatusBadge
            value={screenshot.possible_editing_indicators}
            trueLabel="Present"
            falseLabel="None"
          />
        }
      />
      <ResultRow label="Heuristic score" value={screenshot.heuristic_score?.toFixed(2) ?? '—'} />
      <ResultRow
        label="Dimensions"
        value={
          screenshot.width != null && screenshot.height != null
            ? `${screenshot.width} × ${screenshot.height}`
            : '—'
        }
      />
      <ResultRow label="Image format" value={screenshot.image_format ?? '—'} />
      {screenshot.signals?.length > 0 && (
        <div className="pt-1">
          <p className="text-xs text-gray-500 mb-1">Signals</p>
          <ul className="text-[11px] text-gray-700 space-y-0.5 list-disc list-inside">
            {screenshot.signals.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </div>
      )}
      {screenshot.reason && (
        <p className="text-[11px] text-gray-500 pt-1 italic">{screenshot.reason}</p>
      )}
      <ConfidenceBar value={screenshot.confidence} />
      {screenshot.confidence_note && (
        <p className="text-[10px] text-gray-400 pt-1">{screenshot.confidence_note}</p>
      )}
    </AnalysisCard>
  )
}
