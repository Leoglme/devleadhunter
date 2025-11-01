<template>
  <aside
    :class="[
      'fixed left-0 top-0 h-full bg-[#1a1a1a] border-r border-[#30363d] z-40 transition-transform duration-300',
      isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0',
      isMobile ? 'w-64' : 'w-64'
    ]"
  >
    <!-- Logo / Header -->
    <div class="px-4 py-3.5 border-b border-[#30363d] bg-[#1a1a1a]">
      <div class="flex items-center gap-2">
        <div class="w-6 h-6 rounded-full bg-[#9333ea] flex items-center justify-center">
          <i class="fa-solid fa-gem text-white text-xs"></i>
        </div>
        <h1 class="text-sm font-semibold text-[#f9f9f9]">devleadhunter</h1>
      </div>
    </div>

    <!-- Navigation Links -->
    <nav class="px-2 py-4 flex flex-col gap-2">
      <NuxtLink
        v-for="link in links"
        :key="link.to"
        :to="link.to"
        :class="[
          'flex items-center gap-2 px-3 py-2 rounded text-sm transition-all font-medium',
          isActive(link.to) 
            ? 'btn-sidebar-active text-[#f9f9f9]' 
            : 'text-[#8b949e] hover:btn-sidebar-hover hover:text-[#f9f9f9]'
        ]"
        @click="handleClick"
      >
        <i :class="link.icon" class="w-4 h-4"></i>
        <span>{{ link.label }}</span>
      </NuxtLink>
    </nav>

    <!-- User Info -->
    <div class="absolute bottom-0 left-0 right-0 p-4 border-t border-[#30363d] bg-[#1a1a1a]">
      <!-- User Profile - Clickable -->
      <button
        @click="handleProfile"
        class="w-full mb-2 px-2 py-2 flex items-center gap-2 text-sm rounded-lg hover:bg-[#2a2a2a] transition-all group"
      >
        <div class="w-8 h-8 rounded-full bg-[#050505] border border-[#30363d] flex items-center justify-center flex-shrink-0">
          <span class="text-[#f9f9f9] text-xs font-semibold">
            {{ userInitials }}
          </span>
        </div>
        <div class="flex-1 min-w-0 text-left">
          <p class="font-semibold text-[#f9f9f9] truncate transition-colors">
            {{ userName }}
          </p>
          <p class="text-xs text-[#8b949e] truncate">
            {{ userEmail }}
          </p>
        </div>
      </button>
      
      <button
        @click="handleLogout"
        class="w-full px-3 py-1.5 text-sm text-[#f85149] hover:bg-[#da3633]/20 rounded transition-all"
      >
        Logout
      </button>
    </div>
  </aside>

  <!-- Overlay for mobile -->
  <div
    v-if="isOpen && isMobile"
    class="fixed inset-0 bg-black/70 z-30 md:hidden"
    @click="$emit('toggle')"
  />
</template>

<script setup lang="ts">
import type { Ref } from 'vue';
import { computed } from 'vue';
import { useUserStore } from '~/stores/user';
import { useAuth } from '~/composables/useAuth';

/**
 * Props for the Sidebar component
 */
interface Props {
  /**
   * Whether the sidebar is open
   */
  isOpen: boolean;
  
  /**
   * Whether the viewport is mobile size
   */
  isMobile: boolean;
}

/**
 * Props definition
 */
const props = defineProps<Props>();

/**
 * Emits
 */
const emit = defineEmits<{
  toggle: [];
}>();

/**
 * Navigation links configuration
 */
const links = [
  { to: '/dashboard', label: 'Prospect Search', icon: 'fa-solid fa-magnifying-glass' },
  { to: '/dashboard/campaigns', label: 'Campaigns', icon: 'fa-solid fa-envelope' }
];

/**
 * User store instance
 */
const userStore = useUserStore();

/**
 * Auth composable
 */
const { logout } = useAuth();

/**
 * User name computed property
 */
const userName = computed(() => {
  return userStore.userName || 'User';
});

/**
 * User email computed property
 */
const userEmail = computed(() => {
  return userStore.userEmail;
});

/**
 * User initials computed property
 */
const userInitials = computed(() => {
  const name = userName.value;
  const parts = name.split(' ');
  if (parts.length >= 2) {
    return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
  }
  return name.substring(0, 2).toUpperCase();
});

/**
 * Check if a route is active
 * @param {string} path - Route path to check
 * @returns {boolean} True if the route is active
 */
const isActive = (path: string): boolean => {
  const route = useRoute();
  return route.path === path;
};

/**
 * Handle link click (close sidebar on mobile)
 * @returns {void}
 */
const handleClick = (): void => {
  if (props.isMobile) {
    emit('toggle');
  }
};

/**
 * Handle profile button click
 * @returns {void}
 */
const handleProfile = (): void => {
  navigateTo('/profile');
  handleClick();
};

/**
 * Handle logout button click
 * @returns {void}
 */
const handleLogout = (): void => {
  logout();
  handleClick();
};
</script>
