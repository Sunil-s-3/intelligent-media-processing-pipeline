import { useRef, useState } from 'react'
import { Upload, X, Image as ImageIcon } from 'lucide-react'

const ACCEPTED = ['image/jpeg', 'image/png', 'image/webp', 'image/bmp', 'image/tiff']
const MAX_MB = 10

function fmt(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

export default function UploadCard({ onUpload, uploading }) {
  const inputRef = useRef(null)
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [dragOver, setDragOver] = useState(false)
  const [fileError, setFileError] = useState(null)

  function accept(f) {
    setFileError(null)
    if (!f) return
    if (!ACCEPTED.includes(f.type)) {
      setFileError('Unsupported format. Use JPEG, PNG, WEBP, BMP, or TIFF.')
      return
    }
    if (f.size > MAX_MB * 1024 * 1024) {
      setFileError(`File exceeds ${MAX_MB} MB limit.`)
      return
    }
    setFile(f)
    const url = URL.createObjectURL(f)
    setPreview(url)
  }

  function clear() {
    setFile(null)
    setPreview(null)
    setFileError(null)
    if (inputRef.current) inputRef.current.value = ''
  }

  function onDrop(e) {
    e.preventDefault()
    setDragOver(false)
    const f = e.dataTransfer.files?.[0]
    accept(f)
  }

  function onDragOver(e) {
    e.preventDefault()
    setDragOver(true)
  }

  function handleSubmit() {
    if (file) onUpload(file)
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-4">
        Upload Image
      </h2>

      {!file ? (
        <div
          onDrop={onDrop}
          onDragOver={onDragOver}
          onDragLeave={() => setDragOver(false)}
          onClick={() => inputRef.current?.click()}
          className={`flex flex-col items-center justify-center gap-3 border-2 border-dashed rounded-lg p-10 cursor-pointer transition-colors ${
            dragOver
              ? 'border-blue-400 bg-blue-50'
              : 'border-gray-300 hover:border-gray-400 hover:bg-gray-50'
          }`}
        >
          <Upload className="text-gray-400" size={32} />
          <div className="text-center">
            <p className="text-sm font-medium text-gray-700">
              Drop an image here or click to select
            </p>
            <p className="text-xs text-gray-500 mt-1">
              JPEG, PNG, WEBP, BMP, TIFF — max {MAX_MB} MB
            </p>
          </div>
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPTED.join(',')}
            className="hidden"
            onChange={(e) => accept(e.target.files?.[0])}
          />
        </div>
      ) : (
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-shrink-0">
            {preview ? (
              <img
                src={preview}
                alt="Preview"
                className="w-32 h-32 object-cover rounded border border-gray-200"
              />
            ) : (
              <div className="w-32 h-32 flex items-center justify-center bg-gray-100 rounded border border-gray-200">
                <ImageIcon className="text-gray-400" size={32} />
              </div>
            )}
          </div>
          <div className="flex flex-col justify-between flex-1 min-w-0">
            <div>
              <p className="text-sm font-medium text-gray-800 truncate">{file.name}</p>
              <p className="text-xs text-gray-500 mt-1">{fmt(file.size)}</p>
              <p className="text-xs text-gray-500">{file.type}</p>
            </div>
            <div className="flex gap-2 mt-4">
              <button
                onClick={handleSubmit}
                disabled={uploading}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <Upload size={14} />
                {uploading ? 'Uploading…' : 'Upload'}
              </button>
              <button
                onClick={clear}
                disabled={uploading}
                className="flex items-center gap-2 px-4 py-2 border border-gray-300 text-gray-700 text-sm rounded hover:bg-gray-50 disabled:opacity-50 transition-colors"
              >
                <X size={14} />
                Clear
              </button>
            </div>
          </div>
        </div>
      )}

      {fileError && (
        <p className="mt-3 text-sm text-red-600">{fileError}</p>
      )}
    </div>
  )
}
