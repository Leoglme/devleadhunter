<template>
  <div class="flex items-center justify-center min-h-screen px-4 bg-[#050505]">
    <div class="w-full max-w-sm">
      <h1 class="text-2xl font-semibold text-[#f9f9f9] mb-6 text-center">Login</h1>
      
      <form @submit.prevent="handleSubmit" class="space-y-4">
        <!-- Email -->
        <div>
          <label for="email" class="block text-xs font-medium text-muted mb-1.5">
            Email
          </label>
          <input
            id="email"
            v-model="email"
            type="email"
            required
            placeholder="your@email.com"
            class="input-field"
          />
        </div>

        <!-- Password -->
        <div>
          <label for="password" class="block text-xs font-medium text-muted mb-1.5">
            Password
          </label>
          <input
            id="password"
            v-model="password"
            type="password"
            required
            placeholder="••••••••"
            class="input-field"
          />
        </div>

        <!-- Submit Button -->
        <button
          type="submit"
          :disabled="isLoading"
          class="btn-primary w-full"
        >
          <span v-if="isLoading">Logging in...</span>
          <span v-else>Login</span>
        </button>

        <!-- Sign Up Link -->
        <p class="text-center text-sm text-muted">
          Don't have an account?
          <NuxtLink to="/signup" class="text-[#f9f9f9] hover:underline transition-colors">
            Sign up
          </NuxtLink>
        </p>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Ref } from 'vue';
import { ref } from 'vue';
import { useAuth } from '~/composables/useAuth';

/**
 * Login page
 */
definePageMeta({
  layout: false
});

/**
 * Auth composable
 */
const { login, isLoading } = useAuth();

/**
 * Form state
 */
const email: Ref<string> = ref('');
const password: Ref<string> = ref('');

/**
 * Handle form submission
 * @returns {Promise<void>}
 */
const handleSubmit = async (): Promise<void> => {
  try {
    await login({
      email: email.value,
      password: password.value
    });
  } catch (error) {
    // Error handled by useAuth composable
  }
};
</script>
