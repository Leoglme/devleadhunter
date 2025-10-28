import { defineStore } from 'pinia';
import type { Campaign } from '~/types';
import type { Ref } from 'vue';
import { ref, computed } from 'vue';

/**
 * Pinia store for campaign management
 * @module stores/campaigns
 */

interface CampaignsState {
  campaigns: Campaign[];
  currentCampaign: Campaign | null;
  isLoading: boolean;
}

/**
 * Campaigns store definition
 */
export const useCampaignsStore = defineStore('campaigns', () => {
  // State
  const campaigns: Ref<Campaign[]> = ref([]);
  const currentCampaign: Ref<Campaign | null> = ref(null);
  const isLoading: Ref<boolean> = ref(false);
  const error: Ref<string | null> = ref(null);

  // Getters
  const campaignsCount = computed(() => campaigns.value.length);
  
  const activeCampaigns = computed(() => 
    campaigns.value.filter(c => c.status === 'active')
  );
  
  const completedCampaigns = computed(() => 
    campaigns.value.filter(c => c.status === 'completed')
  );

  /**
   * Fetch all campaigns for the user
   * @returns {Promise<void>} Promise that resolves when fetch is complete
   * @throws {Error} If fetch fails
   * 
   * @example
   * ```typescript
   * await campaignsStore.fetchCampaigns();
   * ```
   */
  async function fetchCampaigns(): Promise<void> {
    try {
      isLoading.value = true;
      error.value = null;
      
      // Mock API call - simulate network delay
      await new Promise(resolve => setTimeout(resolve, 800));
      
      // Mock campaigns data
      const mockCampaigns: Campaign[] = [
        {
          id: '1',
          name: 'Restaurants Paris',
          description: 'Prospection de restaurants parisiens sans site web',
          prospectIds: ['1', '3'],
          status: 'active',
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString()
        },
        {
          id: '2',
          name: 'Artisans Lyon',
          description: 'Campagne artisans à Lyon',
          prospectIds: ['2'],
          status: 'completed',
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString()
        }
      ];
      
      campaigns.value = mockCampaigns;
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch campaigns';
      campaigns.value = [];
    } finally {
      isLoading.value = false;
    }
    
    // TODO: Replace with actual API call
    // const config = useRuntimeConfig();
    // const response = await $fetch<{ data: Campaign[] }>(
    //   `${config.public.apiBase}/api/campaigns`,
    //   {
    //     headers: {
    //       Authorization: `Bearer ${useUserStore().token}`
    //     }
    //   }
    // );
    // campaigns.value = response.data;
  }

  /**
   * Create a new campaign
   * @param {Omit<Campaign, 'id' | 'createdAt' | 'updatedAt'>} data - Campaign data
   * @returns {Promise<Campaign>} Promise that resolves with the created campaign
   * @throws {Error} If creation fails
   * 
   * @example
   * ```typescript
   * const campaign = await campaignsStore.createCampaign({
   *   name: 'Restaurants in Paris',
   *   description: 'Targeting restaurants',
   *   prospectIds: ['123', '456'],
   *   status: 'draft'
   * });
   * ```
   */
  async function createCampaign(
    data: Omit<Campaign, 'id' | 'createdAt' | 'updatedAt'>
  ): Promise<Campaign> {
    try {
      isLoading.value = true;
      error.value = null;
      
      // Mock API call - simulate network delay
      await new Promise(resolve => setTimeout(resolve, 800));
      
      const newCampaign: Campaign = {
        id: 'campaign-' + Date.now(),
        ...data,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
      };
      
      campaigns.value.push(newCampaign);
      return newCampaign;
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to create campaign';
      throw err;
    } finally {
      isLoading.value = false;
    }
    
    // TODO: Replace with actual API call
    // const config = useRuntimeConfig();
    // const response = await $fetch<{ data: Campaign }>(
    //   `${config.public.apiBase}/api/campaigns`,
    //   {
    //     method: 'POST',
    //     headers: {
    //       Authorization: `Bearer ${useUserStore().token}`
    //     },
    //     body: data
    //   }
    // );
    // campaigns.value.push(response.data);
  }

  /**
   * Update campaign
   * @param {string} id - Campaign ID
   * @param {Partial<Campaign>} data - Updated campaign data
   * @returns {Promise<Campaign>} Promise that resolves with the updated campaign
   * @throws {Error} If update fails
   */
  async function updateCampaign(
    id: string, 
    data: Partial<Campaign>
  ): Promise<Campaign> {
    try {
      isLoading.value = true;
      error.value = null;
      
      // Mock API call - simulate network delay
      await new Promise(resolve => setTimeout(resolve, 800));
      
      const index = campaigns.value.findIndex(c => c.id === id);
      if (index !== -1) {
        campaigns.value[index] = { ...campaigns.value[index], ...data, updatedAt: new Date().toISOString() };
        return campaigns.value[index];
      }
      
      throw new Error('Campaign not found');
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to update campaign';
      throw err;
    } finally {
      isLoading.value = false;
    }
    
    // TODO: Replace with actual API call
    // const config = useRuntimeConfig();
    // const response = await $fetch<{ data: Campaign }>(
    //   `${config.public.apiBase}/api/campaigns/${id}`,
    //   {
    //     method: 'PUT',
    //     headers: { Authorization: `Bearer ${useUserStore().token}` },
    //     body: data
    //   }
    // );
  }

  /**
   * Add prospects to campaign
   * @param {string} campaignId - Campaign ID
   * @param {string[]} prospectIds - Array of prospect IDs to add
   * @returns {Promise<void>} Promise that resolves when prospects are added
   * @throws {Error} If update fails
   */
  async function addProspectsToCampaign(
    campaignId: string, 
    prospectIds: string[]
  ): Promise<void> {
    try {
      isLoading.value = true;
      error.value = null;
      
      // Mock API call - simulate network delay
      await new Promise(resolve => setTimeout(resolve, 800));
      
      const campaign = campaigns.value.find(c => c.id === campaignId);
      if (campaign) {
        campaign.prospectIds = [...campaign.prospectIds, ...prospectIds];
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to add prospects';
      throw err;
    } finally {
      isLoading.value = false;
    }
    
    // TODO: Replace with actual API call
    // const config = useRuntimeConfig();
    // await $fetch(
    //   `${config.public.apiBase}/api/campaigns/${campaignId}/prospects`,
    //   {
    //     method: 'POST',
    //     headers: { Authorization: `Bearer ${useUserStore().token}` },
    //     body: { prospectIds }
    //   }
    // );
    // await fetchCampaigns();
  }

  /**
   * Get campaign by ID
   * @param {string} id - Campaign ID
   * @returns {Campaign | undefined} The campaign or undefined if not found
   */
  function getCampaignById(id: string): Campaign | undefined {
    return campaigns.value.find(c => c.id === id);
  }

  return {
    // State
    campaigns,
    currentCampaign,
    isLoading,
    error,
    // Getters
    campaignsCount,
    activeCampaigns,
    completedCampaigns,
    // Actions
    fetchCampaigns,
    createCampaign,
    updateCampaign,
    addProspectsToCampaign,
    getCampaignById
  };
});

