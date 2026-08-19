import { AnalysisCard, ResultRow, StatusBadge, ConfidenceBar } from './AnalysisCard'

function BlurSection({ blur }) {
  if (!blur) return null
  return (
    <div className="mb-4 pb-4 border-b border-gray-100">
      <p className="text-xs font-semibold text-gray-600 mb-2">Blur</p>
      <div className="space-y-1">
        <ResultRow
          label="Detected"
          value={<StatusBadge value={blur.detected} trueLabel="Blur detected" falseLabel="Not blurry" />}
        />
        <ResultRow label="Score" value={blur.score?.toFixed(2) ?? '—'} />
        <ResultRow label="Threshold" value={blur.threshold ?? '—'} />
        <ResultRow label="Method" value={blur.method ?? '—'} />
        {blur.reason && (
          <p className="text-[11px] text-gray-500 pt-1 italic">{blur.reason}</p>
        )}
        <ConfidenceBar value={blur.confidence} />
      </div>
    </div>
  )
}

function BrightnessSection({ brightness }) {
  if (!brightness) return null
  return (
    <div>
      <p className="text-xs font-semibold text-gray-600 mb-2">Brightness</p>
      <div className="space-y-1">
        <ResultRow
          label="Issue"
          value={<StatusBadge value={brightness.issue} trueLabel="Low light" falseLabel="OK" />}
        />
        <ResultRow label="Average brightness" value={brightness.average_brightness?.toFixed(2) ?? '—'} />
        <ResultRow label="Threshold" value={brightness.threshold ?? '—'} />
        <ResultRow label="Method" value={brightness.method ?? '—'} />
        {brightness.reason && (
          <p className="text-[11px] text-gray-500 pt-1 italic">{brightness.reason}</p>
        )}
        <ConfidenceBar value={brightness.confidence} />
      </div>
    </div>
  )
}

export default function ImageQualityCard({ imageQuality }) {
  return (
    <AnalysisCard title="Image Quality">
      <BlurSection blur={imageQuality?.blur} />
      <BrightnessSection brightness={imageQuality?.brightness} />
    </AnalysisCard>
  )
}
