import type { Ref } from 'vue'
import { ref } from 'vue'
import type { ModuleState, ModulesResponse } from '~/types/Module'
import { ApiClient } from '~/services/api'

/** Active module keys, shared across the app so the nav reflects activation everywhere. */
// Seeded with the always-on base module so it never flickers as locked before the first load.
const activeModules: Ref<Set<string>> = ref(new Set(['websites']))

/**
 * Read and toggle the user's active tool modules — gates the module-aware navigation.
 * @returns Helpers to check, load and activate modules.
 */
export function useModules(): {
  isModuleActive: (module: string) => boolean
  loadModules: () => Promise<void>
  activateModule: (module: string) => Promise<void>
} {
  /**
   * Whether a module is currently active.
   * @param module - The API module key.
   * @returns True when active.
   */
  function isModuleActive(module: string): boolean {
    return activeModules.value.has(module)
  }

  /** Load the user's module activation state from the API. */
  async function loadModules(): Promise<void> {
    try {
      const response: ModulesResponse = await ApiClient.get<ModulesResponse>('/api/v1/modules')
      activeModules.value = new Set(
        response.modules
          .filter((state: ModuleState): boolean => state.active)
          .map((state: ModuleState): string => state.module),
      )
    } catch {
      // Keep whatever we had; the nav simply won't reveal gated links.
    }
  }

  /**
   * Activate a module for the user, then reflect it locally.
   * @param module - The API module key to activate.
   */
  async function activateModule(module: string): Promise<void> {
    await ApiClient.post(`/api/v1/modules/${module}/activate`, {})
    activeModules.value = new Set([...activeModules.value, module])
  }

  return { isModuleActive, loadModules, activateModule }
}
