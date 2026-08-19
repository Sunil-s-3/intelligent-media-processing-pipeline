import { Activity } from 'lucide-react'

export default function Header({ health }) {
  const connected = health === 'ok'
  return (
    <header className="bg-white border-b border-gray-200">
      <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Activity className="text-blue-600" size={22} />
          <div>
            <h1 className="text-lg font-semibold text-gray-900 leading-tight">
              Intelligent Media Processing Pipeline
            </h1>
            <p className="text-xs text-gray-500">
              AI-assisted vehicle image analysis with asynchronous processing
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <span
            className={`inline-block w-2 h-2 rounded-full ${
              health === null
                ? 'bg-gray-300'
                : connected
                ? 'bg-green-500'
                : 'bg-red-500'
            }`}
          />
          <span className="text-gray-600">
            {health === null
              ? 'Checking…'
              : connected
              ? 'Backend: Connected'
              : 'Backend: Unavailable'}
          </span>
        </div>
      </div>
    </header>
  )
}
