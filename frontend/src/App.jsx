import { useEffect, useRef, useState } from 'react'
import Header from './components/Header'
import UploadCard from './components/UploadCard'
import ProcessingStatus from './components/ProcessingStatus'
import ImageQualityCard from './components/ImageQualityCard'
import DuplicateCard from './components/DuplicateCard'
import OCRCard from './components/OCRCard'
import VehicleNumberCard from './components/VehicleNumberCard'
import ScreenshotCard from './components/ScreenshotCard'
import { checkHealth, uploadImage, getStatus, getResults } from './services/api'

const POLL_INTERVAL_MS = 2500
const TERMINAL_STATES = new Set(['completed', 'failed'])

export default function App() {
  const [health, setHealth] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [processingId, setProcessingId] = useState(null)
  const [status, setStatus] = useState(null)
  const [failureReason, setFailureReason] = useState(null)
  const [analysis, setAnalysis] = useState(null)
  const [uploadError, setUploadError] = useState(null)
  const pollRef = useRef(null)

  // Health check on mount
  useEffect(() => {
    checkHealth()
      .then((r) => setHealth(r.data?.status ?? 'unknown'))
      .catch(() => setHealth('unavailable'))
  }, [])

  function stopPolling() {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }

  async function pollStatus(id) {
    try {
      const res = await getStatus(id)
      const s = res.data?.status
      setStatus(s)
      if (res.data?.failure_reason) setFailureReason(res.data.failure_reason)

      if (s === 'completed') {
        stopPolling()
        const result = await getResults(id)
        setAnalysis(result.data?.analysis ?? null)
        if (result.data?.failure_reason) setFailureReason(result.data.failure_reason)
      } else if (s === 'failed') {
        stopPolling()
      }
    } catch (err) {
      // Network error while polling — keep trying
      console.warn('Poll error:', err.message)
    }
  }

  function startPolling(id) {
    stopPolling()
    pollStatus(id) // immediate first check
    pollRef.current = setInterval(() => pollStatus(id), POLL_INTERVAL_MS)
  }

  async function handleUpload(file) {
    setUploading(true)
    setUploadError(null)
    setProcessingId(null)
    setStatus(null)
    setFailureReason(null)
    setAnalysis(null)
    stopPolling()

    try {
      const res = await uploadImage(file)
      const id = res.data?.processing_id
      setProcessingId(id)
      setStatus(res.data?.status ?? 'pending')
      startPolling(id)
    } catch (err) {
      const status = err.status
      let msg = err.message
      if (status === 400) msg = 'Invalid or corrupt image file.'
      else if (status === 413) msg = 'File is too large (max 10 MB).'
      else if (status === 415) msg = 'Unsupported image format.'
      else if (status === 503) msg = 'Backend is unavailable. Is Docker Compose running?'
      setUploadError(msg)
    } finally {
      setUploading(false)
    }
  }

  // Cleanup on unmount
  useEffect(() => () => stopPolling(), [])

  return (
    <div className="min-h-screen bg-gray-50">
      <Header health={health} />

      <main className="max-w-5xl mx-auto px-4 py-6 space-y-5">
        <UploadCard onUpload={handleUpload} uploading={uploading} />

        {uploadError && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
            {uploadError}
          </div>
        )}

        <ProcessingStatus
          processingId={processingId}
          status={status}
          failureReason={failureReason}
        />

        {analysis && (
          <>
            <p className="text-xs text-gray-400 text-center">
              Confidence values are heuristic indicators, not calibrated ML probabilities.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <ImageQualityCard imageQuality={analysis.image_quality} />
              <DuplicateCard duplicate={analysis.duplicate} />
              <OCRCard ocr={analysis.ocr} />
              <VehicleNumberCard vehicleNumber={analysis.vehicle_number} />
            </div>
            <ScreenshotCard screenshot={analysis.screenshot} />
          </>
        )}
      </main>
    </div>
  )
}
