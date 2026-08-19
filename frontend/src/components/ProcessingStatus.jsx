import { Loader2, CheckCircle, XCircle, Clock } from 'lucide-react'

const STATUS_CONFIG = {
  pending: {
    icon: Clock,
    color: 'text-yellow-600',
    bg: 'bg-yellow-50',
    border: 'border-yellow-200',
    label: 'Pending',
    description: 'Waiting for the worker to pick up the job…',
  },
  processing: {
    icon: Loader2,
    color: 'text-blue-600',
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    label: 'Processing',
    description: 'Worker is analysing the image…',
    spin: true,
  },
  completed: {
    icon: CheckCircle,
    color: 'text-green-600',
    bg: 'bg-green-50',
    border: 'border-green-200',
    label: 'Completed',
    description: 'Analysis finished successfully.',
  },
  failed: {
    icon: XCircle,
    color: 'text-red-600',
    bg: 'bg-red-50',
    border: 'border-red-200',
    label: 'Failed',
    description: 'Processing failed.',
  },
}

export default function ProcessingStatus({ processingId, status, failureReason }) {
  if (!processingId) return null

  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.pending
  const Icon = cfg.icon

  return (
    <div className={`rounded-lg border p-5 ${cfg.bg} ${cfg.border}`}>
      <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">
        Processing Status
      </h2>
      <div className="flex items-start gap-3">
        <Icon
          className={`mt-0.5 flex-shrink-0 ${cfg.color} ${cfg.spin ? 'animate-spin' : ''}`}
          size={20}
        />
        <div className="min-w-0">
          <p className={`text-sm font-semibold ${cfg.color}`}>{cfg.label}</p>
          <p className="text-xs text-gray-600 mt-0.5">{cfg.description}</p>
          <p className="text-xs text-gray-500 mt-2 font-mono break-all">
            ID: {processingId}
          </p>
          {failureReason && (
            <p className="mt-2 text-sm text-red-700 bg-red-100 rounded px-3 py-2 break-words">
              {failureReason}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
