<template>
  <div>
    <!-- Header -->
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-[32px] font-semibold text-[#f9f9f9]">Credit Usage</h1>
      <NuxtLink 
        to="/dashboard/buy-credits"
        class="text-[#f9f9f9] hover:text-[#8b949e] transition-colors text-sm flex items-center gap-1"
      >
        View Pricing Page
        <i class="fa-solid fa-external-link-alt text-xs"></i>
      </NuxtLink>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="space-y-6">
      <div class="card">
        <div class="animate-pulse space-y-4">
          <div class="h-6 bg-[#2a2a2a] rounded w-1/4"></div>
          <div class="h-32 bg-[#2a2a2a] rounded"></div>
        </div>
      </div>
    </div>

    <!-- Content -->
    <div v-else class="space-y-6">
      <!-- Credit Usage Progress Bar -->
      <div class="card">
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-lg font-semibold text-[#f9f9f9]">Credit Usage</h2>
          <NuxtLink 
            to="/dashboard/buy-credits"
            class="btn-primary text-xs px-4 py-2 h-auto"
          >
            Buy More Credits
          </NuxtLink>
        </div>
        
        <p class="text-xs text-[#8b949e] mb-4">
          Last updated: {{ lastUpdated }}
        </p>

        <!-- Progress Bar Container -->
        <div class="relative">
          <div 
            class="relative h-8 bg-[#050505] rounded-lg border border-[#30363d] overflow-hidden cursor-pointer"
            @mouseenter="showProgressTooltip = true"
            @mouseleave="showProgressTooltip = false"
          >
            <!-- Credits Used -->
            <div 
              :style="{ width: `${usedPercentage}%` }"
              class="absolute left-0 top-0 h-full bg-[#1f6feb] transition-all duration-300"
            ></div>
            
            <!-- Credits Remaining -->
            <div 
              :style="{ width: `${remainingPercentage}%`, left: `${usedPercentage}%` }"
              class="absolute top-0 h-full bg-[#30363d] transition-all duration-300"
            ></div>

            <!-- Labels on Progress Bar -->
            <div class="relative h-full flex items-center px-3 text-xs font-medium">
              <span class="text-[#f9f9f9]">0</span>
              <span class="ml-auto text-[#f9f9f9]">
                {{ totalCredits === -1 || totalCredits === Infinity ? '∞' : totalCredits }}
              </span>
            </div>

            <!-- Tooltip -->
            <div 
              v-if="showProgressTooltip"
              class="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 w-64 bg-[#1a1a1a] border border-[#30363d] rounded-lg shadow-xl p-4 z-50"
            >
              <div class="flex items-center gap-2 mb-2">
                <div class="w-3 h-3 rounded bg-[#1f6feb] flex-shrink-0"></div>
                <span class="text-sm font-medium text-[#f9f9f9]">
                  {{ creditsUsed }} ({{ usedPercentage.toFixed(0) }}%) Credits Used
                </span>
              </div>
              <div class="flex items-center gap-2">
                <div class="w-3 h-3 rounded bg-[#30363d] flex-shrink-0"></div>
                <span class="text-sm font-medium text-[#8b949e]">
                  {{ creditsRemaining }} ({{ remainingPercentage.toFixed(0) }}%) Credits Remaining
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Daily Usage Chart -->
      <div class="card">
        <h2 class="text-lg font-semibold text-[#f9f9f9] mb-4">Daily Credit Usage</h2>
        <div v-if="chartData && chartData.labels && chartData.labels.length > 0" class="h-64">
          <canvas ref="chartCanvasRef"></canvas>
        </div>
        <div v-else class="h-64 flex items-center justify-center text-[#8b949e]">
          <p>No usage data available</p>
        </div>
      </div>

      <!-- Recent Credit Usage List -->
      <div class="card">
        <h2 class="text-lg font-semibold text-[#f9f9f9] mb-4">Recent Credit Usage</h2>
        <div v-if="recentTransactions.length > 0" class="space-y-0">
          <div 
            v-for="transaction in recentTransactions" 
            :key="transaction.id"
            class="flex items-center justify-between py-3 border-b border-[#30363d] last:border-b-0"
          >
            <div class="flex-1">
              <p class="text-sm font-medium text-[#f9f9f9]">
                {{ formatTransactionDescription(transaction) }}
              </p>
              <p class="text-xs text-[#8b949e] mt-1">
                {{ formatTransactionDate(transaction.created_at) }}
              </p>
            </div>
            <div class="text-right">
              <p 
                :class="[
                  'text-sm font-medium',
                  transaction.amount < 0 ? 'text-[#f85149]' : 'text-[#238636]'
                ]"
              >
                {{ transaction.amount < 0 ? '-' : '+' }}{{ Math.abs(transaction.amount) }} credits
              </p>
            </div>
          </div>
        </div>
        <div v-else class="text-center py-12 text-[#8b949e]">
          <p class="text-sm">No transactions yet</p>
        </div>
      </div>

      <!-- CTA Section -->
      <div class="card bg-gradient-to-r from-[#1a1a1a] to-[#050505] border-[#30363d]">
        <div class="flex flex-col md:flex-row items-center justify-between gap-4">
          <div>
            <h3 class="text-lg font-semibold text-[#f9f9f9] mb-2">Need More Credits?</h3>
            <p class="text-sm text-[#8b949e]">
              Purchase credits to continue searching prospects and sending campaigns
            </p>
          </div>
          <NuxtLink 
            to="/dashboard/buy-credits"
            class="btn-primary whitespace-nowrap"
          >
            Buy Credits
          </NuxtLink>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { CreditTransaction } from '~/types';
import type { Ref } from 'vue';
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue';
import {
  Chart,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  type ChartConfiguration
} from 'chart.js';
import * as creditTransactionService from '~/services/creditTransactionService';
import { useUserStore } from '~/stores/user';

/**
 * Dashboard credits page - Display credit usage, history and statistics
 */
definePageMeta({
  layout: 'dashboard',
  middleware: 'auth'
});

/**
 * Register Chart.js components
 */
Chart.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

/**
 * Chart instance reference
 */
let chartInstance: Chart | null = null;
const chartCanvasRef: Ref<HTMLCanvasElement | null> = ref(null);

/**
 * User store instance
 */
const userStore = useUserStore();

/**
 * Loading state
 */
const isLoading: Ref<boolean> = ref(true);

/**
 * Transactions state
 */
const transactions: Ref<CreditTransaction[]> = ref([]);

/**
 * Progress tooltip visibility
 */
const showProgressTooltip: Ref<boolean> = ref(false);

/**
 * Total credits (current balance + used)
 */
const totalCredits = computed(() => {
  const balance = creditsRemaining.value;
  const used = creditsUsed.value;
  
  if (balance === Infinity || balance === -1) {
    return balance;
  }
  
  return balance + used;
});

/**
 * Credits used (sum of negative amounts)
 */
const creditsUsed = computed(() => {
  const used = Math.abs(transactions.value
    .filter(t => t.amount < 0)
    .reduce((sum, t) => sum + t.amount, 0));
  return used;
});

/**
 * Credits remaining
 */
const creditsRemaining = computed(() => {
  const balance = userStore.user?.credits_available ?? userStore.user?.credit_balance;
  if (balance === null || balance === undefined) {
    return 0;
  }
  if (balance === -1) {
    return Infinity;
  }
  return balance;
});

/**
 * Used percentage
 */
const usedPercentage = computed(() => {
  const total = totalCredits.value;
  if (total === 0 || total === Infinity || total === -1) return 0;
  const used = creditsUsed.value;
  if (used === 0) return 0;
  return Math.min((used / total) * 100, 100);
});

/**
 * Remaining percentage
 */
const remainingPercentage = computed(() => {
  const total = totalCredits.value;
  if (total === Infinity || total === -1) return 100;
  return Math.max(100 - usedPercentage.value, 0);
});

/**
 * Last updated timestamp
 */
const lastUpdated = computed(() => {
  if (transactions.value.length === 0) {
    return new Date().toLocaleDateString('fr-FR', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }
  const lastTransaction = transactions.value[0];
  return new Date(lastTransaction.created_at).toLocaleDateString('fr-FR', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
});

/**
 * Recent transactions (last 10)
 */
const recentTransactions = computed(() => {
  return transactions.value.slice(0, 10);
});

/**
 * Chart data - Group transactions by day
 */
const chartData = computed(() => {
  if (transactions.value.length === 0) return null;

  // Group by date and sum negative amounts (usage)
  const dailyUsage: Record<string, number> = {};
  
  transactions.value
    .filter(t => t.amount < 0) // Only usage transactions
    .forEach(transaction => {
      const dateObj = new Date(transaction.created_at);
      const date = dateObj.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric'
      });
      dailyUsage[date] = (dailyUsage[date] || 0) + Math.abs(transaction.amount);
    });

  // Get unique dates and sort them
  const allDates = Object.keys(dailyUsage);
  const sortedDates = allDates.sort((a, b) => {
    const dateA = new Date(a);
    const dateB = new Date(b);
    return dateA.getTime() - dateB.getTime();
  }).slice(-30); // Last 30 days

  const labels = sortedDates;

  const data = labels.map(label => dailyUsage[label] || 0);

  return {
    labels,
    datasets: [
      {
        label: 'Credits Used',
        data,
        backgroundColor: '#1f6feb',
        borderRadius: 4,
        maxBarThickness: 50
      }
    ]
  };
});

/**
 * Chart options
 */
const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: false
    },
    tooltip: {
      backgroundColor: '#1a1a1a',
      titleColor: '#f9f9f9',
      bodyColor: '#8b949e',
      borderColor: '#30363d',
      borderWidth: 1,
      padding: 12,
      displayColors: false,
      callbacks: {
        label: function(context: any) {
          return `${context.parsed.y} credits`;
        }
      }
    }
  },
  scales: {
    x: {
      grid: {
        color: '#30363d',
        display: false
      },
      ticks: {
        color: '#8b949e',
        font: {
          size: 11
        }
      }
    },
    y: {
      grid: {
        color: '#30363d'
      },
      ticks: {
        color: '#8b949e',
        font: {
          size: 11
        },
        callback: function(value: any) {
          return value;
        }
      },
      beginAtZero: true
    }
  }
};

/**
 * Format transaction description
 */
const formatTransactionDescription = (transaction: CreditTransaction): string => {
  if (transaction.transaction_type === 'USAGE') {
    // Try to extract action from description
    const desc = transaction.description.toLowerCase();
    if (desc.includes('search')) return 'Prospect Search';
    if (desc.includes('email') || desc.includes('campaign')) return 'Email Campaign';
    if (desc.includes('prospect')) return 'Prospect Found';
    return transaction.description;
  }
  if (transaction.transaction_type === 'PURCHASE') {
    return 'Credit Purchase';
  }
  if (transaction.transaction_type === 'FREE_GIFT') {
    return 'Free Credits';
  }
  if (transaction.transaction_type === 'REFUND') {
    return 'Credit Refund';
  }
  return transaction.description;
};

/**
 * Format transaction date to relative time
 */
const formatTransactionDate = (dateString: string): string => {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) {
    return 'Today';
  } else if (diffDays === 1) {
    return 'Yesterday';
  } else if (diffDays < 7) {
    return `${diffDays} days ago`;
  } else if (diffDays < 30) {
    const weeks = Math.floor(diffDays / 7);
    return `${weeks} week${weeks > 1 ? 's' : ''} ago`;
  } else {
    return date.toLocaleDateString('fr-FR', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  }
};

/**
 * Load credit transactions
 */
const loadTransactions = async (): Promise<void> => {
  try {
    isLoading.value = true;
    const data = await creditTransactionService.getMyTransactions(0, 1000);
    transactions.value = data;
  } catch (error) {
    console.error('Failed to load transactions:', error);
    transactions.value = [];
  } finally {
    isLoading.value = false;
  }
};

/**
 * Initialize chart
 */
const initChart = (): void => {
  if (!chartCanvasRef.value || !chartData.value) return;
  
  // Destroy existing chart
  if (chartInstance) {
    chartInstance.destroy();
  }

  const config: ChartConfiguration<'bar'> = {
    type: 'bar',
    data: chartData.value,
    options: chartOptions
  };

  chartInstance = new Chart(chartCanvasRef.value, config);
};

/**
 * Watch for chart data changes
 */
watch(chartData, async () => {
  await nextTick();
  initChart();
}, { deep: true });

/**
 * Initialize component
 */
onMounted(async () => {
  await loadTransactions();
  // Wait for next tick to ensure DOM is ready
  await nextTick();
  await new Promise(resolve => setTimeout(resolve, 100));
  initChart();
});

/**
 * Cleanup chart on unmount
 */
onBeforeUnmount(() => {
  if (chartInstance) {
    chartInstance.destroy();
    chartInstance = null;
  }
});
</script>

