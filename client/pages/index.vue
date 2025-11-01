<template>
  <div class="flex items-center justify-center min-h-screen bg-[#050505]">
    <div class="text-center">
      <h1 class="text-4xl font-semibold text-[#f9f9f9] mb-4">devleadhunter</h1>
      <p class="text-muted mb-8">Personal prospect research tool for freelance web developers</p>
      
      <div class="flex gap-3 justify-center">
        <NuxtLink
          to="/login"
          class="btn-primary"
        >
          Login
        </NuxtLink>
        <NuxtLink
          to="/signup"
          class="btn-primary"
        >
          Sign Up
        </NuxtLink>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * Landing page with login and signup options
 */
definePageMeta({
  layout: false
});
</script>
