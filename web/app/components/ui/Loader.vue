<template>
  <div
    :class="['flex flex-col items-center justify-center gap-3.5', fullScreen ? 'fixed inset-0 z-50' : 'py-16']"
    :style="fullScreen ? { backgroundColor: 'var(--app-bg, #f4f1e9)' } : undefined"
    role="status"
    aria-live="polite"
  >
    <div class="loader-ring"></div>
    <p class="text-sm text-[var(--app-ink-soft)]">{{ label }}</p>
  </div>
</template>

<script lang="ts" setup>
/**
 * Loading indicator, in flow by default so it never covers the dashboard navigation.
 * `fullScreen` is reserved for the pre-authentication screens, which have no shell to preserve.
 */
defineProps({
  fullScreen: {
    type: Boolean,
    default: false,
  },
  label: {
    type: String,
    default: 'Chargement…',
  },
})
</script>

<style scoped>
.loader-ring {
  width: 40px;
  height: 40px;
  border: 3px solid var(--app-line, rgba(255, 255, 255, 0.1));
  border-left-color: var(--app-accent, #e8a33c);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@media (prefers-reduced-motion: reduce) {
  .loader-ring {
    animation-duration: 2.4s;
  }
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
