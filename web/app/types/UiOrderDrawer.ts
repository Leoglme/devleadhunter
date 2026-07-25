import type { Order } from '~/services/ordersService'

export type UiOrderDrawerProps = {
  open: boolean
  order: Order | null
  showBack: boolean
}

export type OrderEditForm = {
  amount_euros: number
  business_name: string
  customer_email: string
  domain: string
  status: string
  notes: string
}

export type UiOrderDrawerEmits = {
  close: []
  back: []
  finalize: []
  updated: [order: Order]
  deleted: [orderId: number]
}
