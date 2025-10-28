<template>
  <div class="flex items-center justify-center min-h-screen bg-[#0d1117]">
    <div class="text-center">
      <h1 class="text-4xl font-semibold text-white mb-4">devleadhunter</h1>
      <p class="text-muted mb-8">Personal prospect research tool for freelance web developers</p>
      
      <div class="flex gap-3 justify-center">
        <NuxtLink
          to="/login"
          class="px-3 py-1.5 text-white hover:bg-[#2d333b] rounded-lg transition-all border border-[#30363d] bg-[#21262d]"
        >
          Login
        </NuxtLink>
        <NuxtLink
          to="/signup"
          class="px-3 py-1.5 text-white hover:bg-[#2d333b] rounded-lg transition-all border border-[#30363d] bg-[#21262d]"
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
