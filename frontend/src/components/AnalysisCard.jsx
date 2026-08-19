/** Shared primitives used by all result cards */

export function AnalysisCard({ title, children }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-4">
        {title}
      </h3>
      <div className="space-y-2">{children}</div>
    </div>
  )
}

export function ResultRow({ label, value, mono = false }) {
  return (
    <div className="flex justify-between items-start gap-4 py-1.5 border-b border-gray-100 last:border-0">
      <span className="text-xs text-gray-500 flex-shrink-0 pt-0.5">{label}</span>
      <span
        className={`text-xs text-gray-900 text-right break-all ${
          mono ? 'font-mono' : ''
        }`}
      >
        {value ?? <span className="text-gray-400">—</span>}
      </span>
    </div>
  )
}

export function StatusBadge({ value, trueLabel = 'Yes', falseLabel = 'No', trueIsGood = false }) {
  if (value === null || value === undefined) {
    return <span className="text-xs text-gray-400">—</span>
  }
  const isTrue = Boolean(value)
  // If trueIsGood: true→green, false→neutral grey
  // Otherwise (detected/issue): true→amber, false→green
  let cls
  if (trueIsGood) {
    cls = isTrue
      ? 'bg-green-100 text-green-700'
      : 'bg-gray-100 text-gray-600'
  } else {
    cls = isTrue
      ? 'bg-amber-100 text-amber-700'
      : 'bg-green-100 text-green-700'
  }
  return (
    <span className={`inline-block text-xs font-medium px-2 py-0.5 rounded ${cls}`}>
      {isTrue ? trueLabel : falseLabel}
    </span>
  )
}

export function ConfidenceBar({ value }) {
  if (value === null || value === undefined) return null
  const pct = Math.round(value * 100)
  return (
    <div>
      <div className="flex justify-between items-center mb-1">
        <span className="text-xs text-gray-500">Confidence</span>
        <span className="text-xs text-gray-700 font-medium">{pct}%</span>
      </div>
      <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
        <div
          className="h-full bg-blue-400 rounded-full transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="text-[10px] text-gray-400 mt-1">
        Heuristic indicator — not a calibrated ML probability
      </p>
    </div>
  )
}

export function OCRTextBox({ text }) {
  if (!text) return <span className="text-xs text-gray-400">No text extracted</span>
  return (
    <pre className="text-xs bg-gray-50 border border-gray-200 rounded p-2 whitespace-pre-wrap break-all max-h-40 overflow-y-auto font-mono">
      {text}
    </pre>
  )
}
