import type { PaymentProviderKind } from '~/services/paymentAccountService'

/** Emitted whenever the connection state changes, so a host (e.g. the setup wizard) can react. */
export type PaymentProviderConfigEmits = {
  'connected-change': [isConnected: boolean]
}

/** Sales pitch of one encashment provider, shown on its choice card. */
export type PaymentProviderCard = {
  provider: PaymentProviderKind
  role: string
  pitch: string
  benefits: string[]
  caveat: string | null
}
