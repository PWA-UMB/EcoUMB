import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState, type ChangeEvent } from 'react'
import { Link } from 'react-router-dom'

import { Alert } from '@/components/ui/Alert'
import { Button } from '@/components/ui/Button'
import { classificationApi } from '@/features/classification/classificationApi'
import { describeClassifyError } from '@/features/classification/errors'
import { FeedbackPanel } from '@/features/classification/FeedbackPanel'
import { ResultCard } from '@/features/classification/ResultCard'
import { useCamera } from '@/hooks/useCamera'
import { ACCEPTED_TYPES, captureFrame, prepareImage } from '@/lib/image'

interface Photo {
  blob: Blob
  url: string
}

/** Flujo del Sprint 2: foto (cámara o galería) → clasificación simulada → resultado y registro. */
export function ScanPage() {
  const queryClient = useQueryClient()
  const camera = useCamera()
  const fileInput = useRef<HTMLInputElement>(null)
  const [photo, setPhoto] = useState<Photo | null>(null)
  const [pickError, setPickError] = useState<string | null>(null)

  const classify = useMutation({
    mutationFn: (blob: Blob) => classificationApi.classify(blob),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['history'] }),
  })

  // La vista previa usa una URL local que se libera al cambiar de foto o salir de la pantalla.
  useEffect(() => {
    if (!photo) return
    return () => URL.revokeObjectURL(photo.url)
  }, [photo])

  const keepPhoto = (blob: Blob) => {
    classify.reset()
    setPickError(null)
    setPhoto({ blob, url: URL.createObjectURL(blob) })
  }

  const handleFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    event.target.value = '' // permite volver a elegir el mismo archivo
    if (!file) return
    if (!ACCEPTED_TYPES.includes(file.type)) {
      setPickError('Formato no admitido. Usa una imagen JPEG, PNG o WebP.')
      return
    }
    keepPhoto(await prepareImage(file))
  }

  const handleCapture = async () => {
    if (!camera.videoRef.current) return
    try {
      const blob = await captureFrame(camera.videoRef.current)
      camera.stop()
      keepPhoto(blob)
    } catch {
      setPickError('No se pudo tomar la foto. Intenta de nuevo o elige una de la galería.')
    }
  }

  const reset = () => {
    classify.reset()
    setPickError(null)
    setPhoto(null)
  }

  const isCameraOpen = camera.status === 'starting' || camera.status === 'ready'
  const errorMessage = pickError ?? camera.error

  return (
    <main className="space-y-6">
      <h1 className="font-display text-3xl font-bold tracking-tight">Escanear un residuo</h1>

      <input
        ref={fileInput}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        aria-label="Elegir foto de la galería"
        className="sr-only"
        tabIndex={-1}
        onChange={(event) => void handleFile(event)}
      />

      {classify.data ? (
        <div className="space-y-5">
          <ResultCard result={classify.data} imageUrl={photo?.url} />
          <FeedbackPanel key={classify.data.id} result={classify.data} />
          <div className="flex flex-wrap gap-3">
            <Button onClick={reset}>Escanear otro residuo</Button>
            <Link
              to="/historial"
              className="inline-flex min-h-11 items-center rounded-xl border border-forest-900/20 bg-white px-5 font-semibold text-forest-900 hover:bg-forest-100"
            >
              Ver historial
            </Link>
          </div>
        </div>
      ) : photo ? (
        <section aria-label="Vista previa" className="space-y-4">
          <img
            src={photo.url}
            alt="Vista previa del residuo"
            className="aspect-video w-full rounded-3xl bg-forest-100 object-cover"
          />
          {classify.isError && <Alert tone="error">{describeClassifyError(classify.error)}</Alert>}
          <div className="flex flex-wrap gap-3">
            <Button loading={classify.isPending} onClick={() => classify.mutate(photo.blob)}>
              {classify.isPending ? 'Clasificando…' : 'Clasificar'}
            </Button>
            <Button variant="secondary" disabled={classify.isPending} onClick={reset}>
              Elegir otra foto
            </Button>
          </div>
        </section>
      ) : isCameraOpen ? (
        <section aria-label="Cámara" className="space-y-4">
          <video
            ref={camera.videoRef}
            muted
            playsInline
            aria-label="Vista de la cámara"
            className="aspect-video w-full rounded-3xl bg-forest-950 object-cover"
          />
          {camera.status === 'starting' && (
            <p role="status" className="text-forest-900/70">
              Abriendo la cámara…
            </p>
          )}
          {pickError && <Alert tone="error">{pickError}</Alert>}
          <div className="flex flex-wrap gap-3">
            <Button disabled={camera.status !== 'ready'} onClick={() => void handleCapture()}>
              Tomar foto
            </Button>
            <Button variant="secondary" onClick={camera.stop}>
              Cancelar
            </Button>
          </div>
        </section>
      ) : (
        <section className="space-y-4">
          <p className="text-forest-900/80">
            Toma una foto del residuo o elige una de tu galería y te diremos en qué bolsa va.
          </p>
          {errorMessage && <Alert tone="error">{errorMessage}</Alert>}
          <div className="flex flex-wrap gap-3">
            <Button onClick={() => void camera.start()}>Abrir la cámara</Button>
            <Button variant="secondary" onClick={() => fileInput.current?.click()}>
              Elegir de la galería
            </Button>
          </div>
        </section>
      )}
    </main>
  )
}
