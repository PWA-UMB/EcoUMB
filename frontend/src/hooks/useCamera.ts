import { useCallback, useEffect, useRef, useState } from 'react'

export type CameraStatus = 'idle' | 'starting' | 'ready' | 'error'

function describe(error: unknown): string {
  const name = error instanceof DOMException ? error.name : ''
  if (name === 'NotAllowedError' || name === 'SecurityError') {
    return 'No diste permiso para usar la cámara. Puedes elegir una foto de la galería.'
  }
  if (name === 'NotFoundError' || name === 'OverconstrainedError') {
    return 'No se encontró una cámara en este dispositivo. Puedes elegir una foto de la galería.'
  }
  return 'No se pudo abrir la cámara. Puedes elegir una foto de la galería.'
}

/** Abre la cámara trasera con la API MediaDevices y libera el hardware al cerrar o desmontar. */
export function useCamera() {
  const videoRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const [status, setStatus] = useState<CameraStatus>('idle')
  const [error, setError] = useState<string | null>(null)

  const stop = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
    setStatus('idle')
  }, [])

  const start = useCallback(async () => {
    setError(null)
    if (!navigator.mediaDevices?.getUserMedia) {
      setError('Este navegador no permite usar la cámara. Puedes elegir una foto de la galería.')
      setStatus('error')
      return
    }
    setStatus('starting')
    try {
      streamRef.current = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: 'environment' } },
        audio: false,
      })
      setStatus('ready')
    } catch (failure) {
      setError(describe(failure))
      setStatus('error')
    }
  }, [])

  // Cuando hay flujo y el <video> ya existe, se conecta y se reproduce.
  useEffect(() => {
    const video = videoRef.current
    if (status === 'ready' && video && streamRef.current) {
      video.srcObject = streamRef.current
      void video.play?.()
    }
  }, [status])

  useEffect(() => stop, [stop])

  return { videoRef, status, error, start, stop }
}
