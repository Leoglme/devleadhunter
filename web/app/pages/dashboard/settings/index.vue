<template>
  <div class="py-16 text-center text-sm text-[var(--app-ink-soft)]">Redirection vers les paramètres…</div>
</template>

<script lang="ts" setup>
// Les Paramètres vivent dans le sous-panneau de la sidebar : cette route nue arrivait sur la 404.
definePageMeta({
  layout: 'dashboard',
  middleware: 'auth',
})

await navigateTo('/dashboard/settings/sending', { replace: true })
</script>
