<template>
  <div>
    <h1 class="text-[32px] font-semibold text-[#f9f9f9] mb-4">Prospect Search</h1>

    <!-- Search Form -->
    <div class="card mb-6">
      <h2 class="text-sm font-semibold text-[#f9f9f9] mb-3">Search Criteria</h2>
      <UiSearchForm />
    </div>

    <!-- Results -->
    <div v-if="prospectsStore.isLoading" class="card">
      <div class="animate-pulse space-y-3">
        <div class="h-4 bg-[#2a2a2a] rounded w-3/4"></div>
        <div class="h-4 bg-[#2a2a2a] rounded w-full"></div>
        <div class="h-4 bg-[#2a2a2a] rounded w-5/6"></div>
      </div>
    </div>

    <div v-else-if="prospectsStore.prospects.length > 0" class="card">
      <div class="mb-4 flex justify-between items-center">
        <h2 class="text-base font-semibold text-[#f9f9f9]">
          Results ({{ prospectsStore.prospectsCount }})
        </h2>
        <div class="flex gap-3 text-xs text-muted">
          <span class="text-[#DC4747]">No Website: {{ prospectsStore.prospectsWithoutWebsite.length }}</span>
          <span class="text-muted">•</span>
          <span class="text-[#2BAD5F]">Has Website: {{ prospectsStore.prospectsWithWebsite.length }}</span>
        </div>
      </div>
      <UiProspectTable :prospects="prospectsStore.prospects" />
    </div>

    <div v-else-if="prospectsStore.hasSearched" class="card text-center py-12">
      <i class="fa-solid fa-magnifying-glass text-5xl text-[#8b949e] mb-3"></i>
      <p class="text-[#8b949e]">Start a search to find prospects</p>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * Dashboard home page - Prospect Search
 */
definePageMeta({
  layout: 'dashboard',
  middleware: 'auth'
});

/**
 * Prospects store
 */
const prospectsStore = useProspectsStore();
</script>
