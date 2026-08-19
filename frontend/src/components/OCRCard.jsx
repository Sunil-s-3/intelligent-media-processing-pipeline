import { AnalysisCard, ResultRow, ConfidenceBar, OCRTextBox } from './AnalysisCard'

const STATUS_LABEL = {
  completed: 'Completed',
  unavailable: 'Unavailable (Tesseract not found)',
  failed: 'Failed',
}

export default function OCRCard({ ocr }) {
  if (!ocr) return null
  return (
    <AnalysisCard title="OCR">
      <ResultRow
        label="Status"
        value={STATUS_LABEL[ocr.status] ?? ocr.status ?? '—'}
      />
      <ResultRow label="Word count" value={ocr.word_count ?? '—'} />
      <div className="pt-1">
        <p className="text-xs text-gray-500 mb-1">Extracted text</p>
        <OCRTextBox text={ocr.ocr_text} />
      </div>
      {ocr.cleaned_text && ocr.cleaned_text !== ocr.ocr_text && (
        <div className="pt-1">
          <p className="text-xs text-gray-500 mb-1">Cleaned text</p>
          <OCRTextBox text={ocr.cleaned_text} />
        </div>
      )}
      {ocr.reason && (
        <p className="text-[11px] text-gray-500 pt-1 italic">{ocr.reason}</p>
      )}
      <ConfidenceBar value={ocr.confidence} />
    </AnalysisCard>
  )
}
