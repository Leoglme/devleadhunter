export type UiConfirmModalConfirmButtonVariant = 'danger' | 'primary'

export type UiConfirmModalProps = {
  title?: string
  message?: string
  confirmText?: string
  cancelText?: string
  confirmButtonVariant?: UiConfirmModalConfirmButtonVariant
}
