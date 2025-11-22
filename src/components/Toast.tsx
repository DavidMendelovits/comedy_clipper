import { useEffect, useState } from 'react'
import { CheckCircle, XCircle, AlertCircle, X } from 'lucide-react'
import Card from './ui/Card'

interface ToastProps {
  message: string
  type: 'success' | 'error' | 'info' | 'warning'
  duration?: number
  onClose: () => void
}

export default function Toast({ message, type, duration = 4000, onClose }: ToastProps) {
  const [isExiting, setIsExiting] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => {
      handleClose()
    }, duration)

    return () => clearTimeout(timer)
  }, [duration, onClose])

  const handleClose = () => {
    setIsExiting(true)
    setTimeout(() => {
      onClose()
    }, 300)
  }

  const getIcon = () => {
    switch (type) {
      case 'success':
        return <CheckCircle className="w-5 h-5 text-emerald-400" />
      case 'error':
        return <XCircle className="w-5 h-5 text-red-400" />
      case 'warning':
        return <AlertCircle className="w-5 h-5 text-amber-400" />
      case 'info':
        return <AlertCircle className="w-5 h-5 text-cyan-400" />
    }
  }

  const getStyles = () => {
    switch (type) {
      case 'success':
        return {
          bg: 'bg-emerald-900/90',
          border: 'border-emerald-600/50',
          text: 'text-emerald-100',
          glow: 'shadow-emerald-500/30',
          iconBg: 'bg-emerald-500/20'
        }
      case 'error':
        return {
          bg: 'bg-red-900/90',
          border: 'border-red-600/50',
          text: 'text-red-100',
          glow: 'shadow-red-500/30',
          iconBg: 'bg-red-500/20'
        }
      case 'warning':
        return {
          bg: 'bg-amber-900/90',
          border: 'border-amber-600/50',
          text: 'text-amber-100',
          glow: 'shadow-amber-500/30',
          iconBg: 'bg-amber-500/20'
        }
      case 'info':
        return {
          bg: 'bg-cyan-900/90',
          border: 'border-cyan-600/50',
          text: 'text-cyan-100',
          glow: 'shadow-cyan-500/30',
          iconBg: 'bg-cyan-500/20'
        }
    }
  }

  const styles = getStyles()

  return (
    <div
      className={`fixed top-6 right-6 z-50 transition-all duration-300 ${
        isExiting ? 'animate-slide-out-right' : 'animate-slide-in-right'
      }`}
    >
      <Card
        variant="glass"
        padding="none"
        className={`${styles.bg} ${styles.border} border-2 shadow-2xl ${styles.glow} max-w-md`}
      >
        <div className="flex items-center gap-3 px-4 py-3">
          <div className={`flex-shrink-0 p-2 rounded-lg ${styles.iconBg}`}>
            {getIcon()}
          </div>
          <span className={`font-medium flex-1 ${styles.text}`}>{message}</span>
          <button
            onClick={handleClose}
            className="flex-shrink-0 p-1.5 hover:bg-white/10 rounded-lg transition-all hover:scale-110 active:scale-95"
            aria-label="Close notification"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        {/* Progress bar */}
        <div className="h-1 bg-white/10 overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-white/40 to-white/60"
            style={{
              animation: `shrink ${duration}ms linear forwards`
            }}
          />
        </div>
        <style>{`
          @keyframes shrink {
            from { width: 100%; }
            to { width: 0%; }
          }
        `}</style>
      </Card>
    </div>
  )
}
