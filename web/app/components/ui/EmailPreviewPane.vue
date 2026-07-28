<template>
  <div class="rounded-lg border border-[var(--app-line)] bg-white p-6">
    <div class="mb-4 border-b border-neutral-200 pb-4">
      <p class="text-xs text-neutral-500">Sujet :</p>
      <p class="text-sm font-medium text-neutral-900">{{ subject }}</p>
    </div>
    <!-- eslint-disable-next-line vue/no-v-html -- Preview of the user's own email template HTML -->
    <div class="prose max-w-none text-sm text-neutral-900" v-html="bodyHtml"></div>
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
