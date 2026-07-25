/** Emitted whenever the connection state changes, so a host (e.g. the setup wizard) can react. */
export type PaymentProviderConfigEmits = {
  'connected-change': [isConnected: boolean]
}
