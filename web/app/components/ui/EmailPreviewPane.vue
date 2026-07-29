<template>
  <div class="min-w-0 rounded-lg border border-[var(--app-line)] bg-white p-6">
    <div class="mb-4 border-b border-neutral-200 pb-4">
      <p class="text-xs text-neutral-500">Sujet :</p>
      <p class="text-sm font-medium break-words text-neutral-900">{{ subject }}</p>
    </div>
    <!-- Without this scroll container, a fixed-width signature table widens the whole drawer. -->
    <div class="email-preview-pane__body overflow-x-auto">
      <!-- eslint-disable-next-line vue/no-v-html -- Preview of the user's own email template HTML -->
      <div class="prose max-w-none text-sm text-neutral-900" v-html="bodyHtml"></div>
    </div>
  </div>
</template>

<script lang="ts" setup>
/** Rendered email, on the white background a mail client would use. */
defineProps({
  subject: {
    type: String,
    default: '',
  },
  bodyHtml: {
    type: String,
    default: '',
  },
})
</script>

<style scoped>
/* The body is arbitrary user HTML — reined in here rather than trusted. */
.email-preview-pane__body :deep(img) {
  max-width: 100%;
  height: auto;
}

.email-preview-pane__body :deep(table) {
  max-width: 100%;
}

.email-preview-pane__body :deep(a) {
  word-break: break-word;
}
</style>
