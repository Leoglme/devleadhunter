<template>
  <UApp>
    <NuxtLoadingIndicator color="var(--app-ink)" :height="2" :throttle="200" />
    <DevLeadHunterDesktopUpdaterPanel />
    <DevLeadHunterDevToolbar />
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
    <UiToastHost />
  </UApp>
</template>

<script lang="ts" setup>
/**
 * Root application shell. Auth initialization runs in the auth.client plugin.
 */
</script>
