<template>
  <div id="__nuxt">
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
  </div>
</template>

<script setup lang="ts">
/**
 * Root component
 * Initializes user store authentication
 */

/**
 * User store
 */
const userStore = useUserStore();

/**
 * Initialize authentication on app mount
 */
onMounted(() => {
  userStore.initializeAuth();
});
</script>

<style>
/* Prevent flash of unstyled content */
#__nuxt {
  visibility: hidden;
}

#__nuxt.html-ready {
  visibility: visible;
}
</style>


