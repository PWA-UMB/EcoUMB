import { request } from '@/lib/api'

export interface BagItem {
  code: string
  display_name: string
  disposal_tip: string
}

export interface Bag {
  category: string
  bag_color: string
  description: string
  educational_text: string
  items: BagItem[]
}

export interface EducationContent {
  normative: { title: string; summary: string; note: string }
  bags: Bag[]
  practices: { title: string; text: string }[]
}

export const educationApi = {
  get: () => request<EducationContent>('/api/v1/education'),
}
