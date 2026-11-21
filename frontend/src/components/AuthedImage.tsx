import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import { classificationApi } from '@/features/classification/classificationApi'

interface AuthedImageProps {
  /** Ruta de la API de la foto guardada (`image_url`). Se descarga con el token del usuario. */
  path: string
  alt: string
  className?: string
}

/** La foto guardada está protegida: no se puede usar en un `<img src>` directo, se descarga con el token. */
export function AuthedImage({ path, alt, className }: AuthedImageProps) {
  const { data: blob, isError } = useQuery({
    queryKey: ['image', path],
    queryFn: () => classificationApi.image(path),
    staleTime: Infinity,
    retry: false,
  })
  const [url, setUrl] = useState<string | null>(null)

  useEffect(() => {
    if (!blob) return
    const objectUrl = URL.createObjectURL(blob)
    setUrl(objectUrl)
    return () => URL.revokeObjectURL(objectUrl)
  }, [blob])

  if (url) return <img src={url} alt={alt} className={className} />
  return (
    <div
      role="img"
      aria-label={isError ? 'Foto no disponible' : 'Cargando foto'}
      className={`${className ?? ''} grid place-items-center bg-forest-100 text-xs text-forest-900/60`}
    >
      {isError ? 'Sin foto' : ''}
    </div>
  )
}
