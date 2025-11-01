<template>
  <div class="flex h-screen bg-[#050505]">
    <!-- Sidebar -->
    <UiSidebar
      :is-open="isSidebarOpen"
      :is-mobile="isMobile"
      @toggle="toggleSidebar"
    />

    <!-- Main Content -->
    <div class="flex-1 flex flex-col overflow-hidden ml-0 md:ml-64">
      <!-- Mobile Header -->
      <header class="md:hidden bg-[#1a1a1a] border-b border-[#30363d] px-4 py-3 sticky top-0 z-10">
        <div class="flex items-center justify-between">
          <button
            @click="toggleSidebar"
            class="text-[#8b949e] hover:text-[#f9f9f9] transition-colors"
          >
            <i class="fa-solid fa-bars w-5 h-5"></i>
          </button>
          <h1 class="text-sm font-semibold text-[#f9f9f9]">devleadhunter</h1>
          <div class="w-5" />
        </div>
      </header>

      <!-- Page Content -->
      <main class="flex-1 overflow-y-auto px-4 py-6 md:px-8">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Ref } from 'vue';
import { ref, onMounted, onUnmounted } from 'vue';

/**
 * Sidebar state
 */
const isSidebarOpen: Ref<boolean> = ref(false);

/**
 * Mobile state
 */
const isMobile: Ref<boolean> = ref(false);

/**
 * Check if viewport is mobile size
 * @returns {void}
 */
const checkMobile = (): void => {
  if (process.client) {
    isMobile.value = window.innerWidth < 768;
    if (!isMobile.value) {
      isSidebarOpen.value = true;
    }
  }
};

/**
 * Toggle sidebar
 * @returns {void}
 */
const toggleSidebar = (): void => {
  isSidebarOpen.value = !isSidebarOpen.value;
};

/**
 * Handle window resize
 * @returns {void}
 */
const handleResize = (): void => {
  checkMobile();
};

// Lifecycle hooks
onMounted(() => {
  checkMobile();
  if (process.client) {
    window.addEventListener('resize', handleResize);
  }
});

onUnmounted(() => {
  if (process.client) {
    window.removeEventListener('resize', handleResize);
  }
});
</script>

