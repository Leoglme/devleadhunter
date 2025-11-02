<template>
  <div>
    <div v-if="isInitializing" class="fixed inset-0 bg-[#050505] flex items-center justify-center z-50">
      <div class="loader-smooth"></div>
    </div>
    <div v-else class="flex h-screen bg-[#050505] w-full">
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
          <div v-if="showCreditsPopover && isMobile" 
               class="fixed inset-0 z-40" 
               @click="handleClickOutside"></div>
          <div class="flex items-center justify-between">
            <button
              @click="toggleSidebar"
              class="text-[#8b949e] hover:text-[#f9f9f9] transition-colors"
            >
              <i class="fa-solid fa-bars w-5 h-5"></i>
            </button>
            <div class="flex items-center gap-3 flex-1 justify-center">
              <h1 class="text-sm font-semibold text-[#f9f9f9]">devleadhunter</h1>
            </div>
            <!-- Mobile Credits Icon -->
            <div class="relative z-50">
              <button 
                @click.stop="toggleCreditsPopover"
                :class="['w-8 h-8 rounded-full bg-[#1a1a1a] border-2 flex items-center justify-center text-[#f9f9f9] font-semibold', creditBorderColor, creditTextSize]">
                {{ creditIconValue }}
              </button>
              <!-- Mobile Popover -->
              <div v-if="showCreditsPopover && isMobile" 
                   class="absolute right-0 top-10 w-72 bg-[#1a1a1a] rounded-lg shadow-xl p-4 z-50 border border-[#30363d]"
                   @click.stop>
                <div class="flex items-start gap-4 mb-3">
                  <div :class="['w-14 h-14 rounded-full bg-[#1a1a1a] border-2 flex items-center justify-center text-[#f9f9f9] font-semibold flex-shrink-0', creditBorderColor, creditTextSizeLarge]">
                    {{ creditIconValue }}
                  </div>
                  <div class="flex-1 min-w-0">
                    <p class="font-bold text-[#f9f9f9] uppercase text-sm mb-1">Remaining Credits</p>
                    <p class="text-xs text-[#8b949e] leading-relaxed">Used to search and find prospects for your campaigns and send emails</p>
                  </div>
                </div>
                <NuxtLink 
                  to="/dashboard/buy-credits"
                  class="flex items-center justify-center w-full text-center btn-secondary text-xs px-3 py-2"
                  @click="showCreditsPopover = false"
                >
                  Refill now
                </NuxtLink>
              </div>
            </div>
          </div>
        </header>

        <!-- Page Content -->
        <main class="flex-1 overflow-y-auto px-4 py-6 md:px-8">
          <slot />
        </main>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Ref } from 'vue';
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useUserStore } from '~/stores/user';

/**
 * Auth initialization state
 */
const isInitializing: Ref<boolean> = ref(true);

/**
 * Sidebar state
 */
const isSidebarOpen: Ref<boolean> = ref(false);

/**
 * Mobile state
 */
const isMobile: Ref<boolean> = ref(false);

/**
 * Credits popover visibility state
 */
const showCreditsPopover: Ref<boolean> = ref(false);

/**
 * User store instance
 */
const userStore = useUserStore();

/**
 * Credit icon value for circular icon
 */
const creditIconValue = computed(() => {
  const credits = userStore.user?.credits_available ?? userStore.user?.credit_balance;
  if (credits === null || credits === undefined) {
    return '0';
  }
  if (credits === -1) {
    return '∞';
  }
  // Always show the real number of credits
  return credits.toString();
});

/**
 * Credit border color based on remaining credits
 */
const creditBorderColor = computed(() => {
  const credits = userStore.user?.credits_available ?? userStore.user?.credit_balance;
  if (credits === null || credits === undefined || credits === 0) {
    return 'border-[#DC4747]'; // Red for no credits
  }
  if (credits === -1) {
    return 'border-[#30363d]'; // Default gray for unlimited
  }
  if (credits <= 10) {
    return 'border-[#DC4747]'; // Red for low credits
  }
  return 'border-[#2BAD5F]'; // Green for sufficient credits
});

/**
 * Credit text size based on remaining credits
 * Smaller font if 1000 or more
 */
const creditTextSize = computed(() => {
  const credits = userStore.user?.credits_available ?? userStore.user?.credit_balance;
  if (credits === null || credits === undefined || credits === -1) {
    return 'text-xs';
  }
  if (credits >= 1000) {
    return 'text-[10px]';
  }
  return 'text-xs';
});

/**
 * Credit text size for large popover icon
 * Smaller font if 1000 or more
 */
const creditTextSizeLarge = computed(() => {
  const credits = userStore.user?.credits_available ?? userStore.user?.credit_balance;
  if (credits === null || credits === undefined || credits === -1) {
    return 'text-lg';
  }
  if (credits >= 1000) {
    return 'text-sm';
  }
  return 'text-lg';
});

/**
 * Toggle credits popover (for mobile click)
 */
const toggleCreditsPopover = (): void => {
  showCreditsPopover.value = !showCreditsPopover.value;
};

/**
 * Handle click outside to close popover
 */
const handleClickOutside = (): void => {
  showCreditsPopover.value = false;
};

/**
 * Initialize authentication
 * @returns {Promise<void>}
 */
async function initializeAuth(): Promise<void> {
  if (process.client) {
    // Small delay to ensure store is hydrated from localStorage
    await new Promise(resolve => setTimeout(resolve, 300));
    isInitializing.value = false;
  }
}

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
onMounted(async () => {
  await initializeAuth();
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

<style scoped>
.loader-smooth {
  width: 60px;
  height: 60px;
  border: 4px solid rgba(255, 255, 255, 0.1);
  border-left-color: #f9f9f9;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>

