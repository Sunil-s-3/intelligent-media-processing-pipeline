import { AnalysisCard, ResultRow, StatusBadge, ConfidenceBar } from './AnalysisCard'

export default function DuplicateCard({ duplicate }) {
  if (!duplicate) return null
  return (
    <AnalysisCard title="Duplicate Detection">
      <ResultRow
        label="Detected"
        value={
          <StatusBadge
            value={duplicate.detected}
            trueLabel="Duplicate found"
            falseLabel="No duplicate"
          />
        }
      />
      <ResultRow
        label="Similarity"
        value={
          duplicate.similarity != null
            ? `${(duplicate.similarity * 100).toFixed(1)}%`
            : '—'
        }
      />
      <ResultRow label="Hamming distance" value={duplicate.hamming_distance ?? '—'} />
      <ResultRow label="Threshold" value={duplicate.threshold ?? '—'} />
      <ResultRow label="Method" value={duplicate.method ?? '—'} />
      <ResultRow
        label="Matched image ID"
        value={duplicate.matched_image_id ?? 'None'}
        mono
      />
      <ResultRow
        label="Perceptual hash"
        value={duplicate.perceptual_hash ?? '—'}
        mono
      />
      {duplicate.reason && (
        <p className="text-[11px] text-gray-500 pt-1 italic">{duplicate.reason}</p>
      )}
      <ConfidenceBar value={duplicate.confidence} />
    </AnalysisCard>
  )
}
