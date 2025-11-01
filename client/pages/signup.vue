<template>
  <div class="flex items-center justify-center min-h-screen px-4 bg-[#050505]">
    <div class="w-full max-w-sm">
      <h1 class="text-2xl font-semibold text-[#f9f9f9] mb-6 text-center">Sign Up</h1>
      
      <form @submit.prevent="handleSubmit" class="space-y-4">
        <!-- Name -->
        <div>
          <label for="name" class="block text-xs font-medium text-muted mb-1.5">
            Name
          </label>
          <input
            id="name"
            v-model="name"
            type="text"
            required
            placeholder="John Doe"
            class="input-field"
          />
        </div>

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
          <span v-if="isLoading">Creating account...</span>
          <span v-else>Sign Up</span>
        </button>

        <!-- Login Link -->
        <p class="text-center text-sm text-muted">
          Already have an account?
          <NuxtLink to="/login" class="text-[#f9f9f9] hover:underline transition-colors">
            Login
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
 * Signup page
 */
definePageMeta({
  layout: false
});

/**
 * Auth composable
 */
const { signup, isLoading } = useAuth();

/**
 * Form state
 */
const name: Ref<string> = ref('');
const email: Ref<string> = ref('');
const password: Ref<string> = ref('');

/**
 * Handle form submission
 * @returns {Promise<void>}
 */
const handleSubmit = async (): Promise<void> => {
  try {
    await signup({
      name: name.value,
      email: email.value,
      password: password.value
    });
  } catch (error) {
    // Error handled by useAuth composable
  }
};
</script>
