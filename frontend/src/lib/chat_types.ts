export type DeliveryState = 'pending' | 'saved' | 'failed'

export interface ChatMessage {
  localId: string
  entry_id: string | null
  raw_text: string
  logged_at: string
  updated_at: string
  isEdited: boolean
  delivery: DeliveryState
}
