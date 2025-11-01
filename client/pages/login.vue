<template>
  <div>
    <UiLoader v-if="isLoading" />
    <div v-else class="flex items-center justify-center min-h-screen px-4 bg-[#050505]">
      <div class="w-full max-w-sm">
        <h1 class="text-2xl font-semibold text-[#f9f9f9] mb-6 text-center">Login</h1>
        
        <form @submit.prevent="handleSubmit" class="space-y-4">
          <!-- General Error -->
          <div v-if="generalError" class="text-sm text-[#f85149]">
            {{ generalError }}
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
              placeholder="Saisissez votre adresse e-mail"
              :class="['input-field', emailError && 'border-[#f85149]']"
            />
            <p v-if="emailError" class="mt-1 text-xs text-[#f85149]">{{ emailError }}</p>
          </div>

          <!-- Password -->
          <div>
            <label for="password" class="block text-xs font-medium text-muted mb-1.5">
              Mot de passe
            </label>
            <input
              id="password"
              v-model="password"
              type="password"
              required
              placeholder="Entrez votre mot de passe"
              :class="['input-field', passwordError && 'border-[#f85149]']"
            />
            <p v-if="passwordError" class="mt-1 text-xs text-[#f85149]">{{ passwordError }}</p>
          </div>

          <!-- Submit Button -->
          <button
            type="submit"
            :disabled="isLoading"
            class="btn-primary w-full"
          >
            <span v-if="isLoading">Logging in...</span>
            <span v-else>Se connecter</span>
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
 * Error state
 */
const emailError: Ref<string> = ref('');
const passwordError: Ref<string> = ref('');
const generalError: Ref<string> = ref('');

/**
 * Validate email format
 * @param {string} email - Email to validate
 * @returns {boolean} True if valid
 */
const validateEmail = (email: string): boolean => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};

/**
 * Handle form submission
 * @returns {Promise<void>}
 */
const handleSubmit = async (): Promise<void> => {
  // Reset errors
  emailError.value = '';
  passwordError.value = '';
  generalError.value = '';

  // Validate email
  if (!email.value) {
    emailError.value = 'Pour accéder à votre compte, saisissez votre adresse e-mail.';
    return;
  }
  
  if (!validateEmail(email.value)) {
    emailError.value = 'Format d\'e-mail invalide.';
    return;
  }

  // Validate password
  if (!password.value) {
    passwordError.value = 'Saisissez votre mot de passe.';
    return;
  }

  // Try to login
  try {
    await login({
      email: email.value,
      password: password.value
    });
  } catch (error) {
    // Set general error message
    generalError.value = 'Vos identifiants de connexion sont incorrects. Réessayez.';
  }
};
</script>
