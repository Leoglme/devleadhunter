export type UiPresenterVideoDropzoneProps = {
  selectedFile?: File | null
  isDragging?: boolean
  isUploading?: boolean
  compact?: boolean
  pickedClipPreviewUrl?: string | null
  isCompressing?: boolean
  compressionProgress?: number
  bytesBeforeCompression?: number | null
  sizeErrorMessage?: string | null
}
