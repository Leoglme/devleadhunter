import type { Order } from '~/services/ordersService'
import type { OrderDrawerMode } from '~/types/DrawerStack'

export type UiOrderDrawerProps = {
  open: boolean
  order: Order | null
  mode: OrderDrawerMode
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
  created: [order: Order]
  updated: [order: Order]
  deleted: [orderId: number]
}
