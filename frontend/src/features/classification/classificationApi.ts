import { request, requestBlob } from '@/lib/api'

export type ConfidenceBand = 'high' | 'medium' | 'low'

export interface Candidate {
  code: string
  display_name: string
  bag_color: string
  confidence: number
}

export interface Feedback {
  item: { code: string; display_name: string }
  category: { code: string; bag_color: string }
  /** `false` = el usuario confirmó lo que predijo el modelo. */
  was_corrected: boolean
}

export interface ClassificationResult {
  id: string
  created_at: string
  /** `true` mientras la clasificación la genera el modelo simulado (Sprint 2). */
  simulated: boolean
  /** Versión del modelo real que clasificó (`null` si el resultado es simulado). */
  model_version: string | null
  confidence: number
  confidence_band: ConfidenceBand
  item: { code: string; display_name: string }
  category: { code: string; bag_color: string }
  message: string
  tip: string
  points_awarded: number
  top3: Candidate[]
  image_url: string
  feedback: Feedback | null
}

export interface HistoryPage {
  items: ClassificationResult[]
  total: number
  limit: number
  offset: number
}

const EXTENSION: Record<string, string> = { 'image/png': 'png', 'image/webp': 'webp' }

export const classificationApi = {
  classify: (image: Blob) => {
    const form = new FormData()
    form.append('image', image, `residuo.${EXTENSION[image.type] ?? 'jpg'}`)
    return request<ClassificationResult>('/api/v1/classifications', { method: 'POST', body: form })
  },

  history: (limit: number, offset: number) =>
    request<HistoryPage>(`/api/v1/classifications/me?limit=${limit}&offset=${offset}`),

  /** RF-29/RF-30: confirma o corrige lo que era el residuo. */
  sendFeedback: (id: string, itemCode: string) =>
    request<ClassificationResult>(`/api/v1/classifications/${id}/feedback`, {
      method: 'PUT',
      body: { item_code: itemCode },
    }),

  /** La foto está protegida: solo su dueño la descarga, con su token. */
  image: (path: string) => requestBlob(path),
}
