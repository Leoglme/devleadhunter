<template>
  <div>
    <UiLoader v-if="isLoading" />
    <div v-else class="flex items-center justify-center min-h-screen px-4 bg-[#050505]">
    <div class="w-full max-w-sm">
        <h1 class="text-2xl font-semibold text-[#f9f9f9] mb-6 text-center">Sign Up</h1>
      
      <form @submit.prevent="handleSubmit" class="space-y-4">
          <!-- General Error -->
          <div v-if="generalError" class="text-sm text-[#f85149]">
            {{ generalError }}
          </div>

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
              :class="['input-field', nameError && 'border-[#f85149]']"
          />
            <p v-if="nameError" class="mt-1 text-xs text-[#f85149]">{{ nameError }}</p>
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
              placeholder="Enter your email address"
              :class="['input-field', emailError && 'border-[#f85149]']"
          />
            <p v-if="emailError" class="mt-1 text-xs text-[#f85149]">{{ emailError }}</p>
        </div>

        <!-- Password -->
        <div>
          <label for="password" class="block text-xs font-medium text-muted mb-1.5">
            Password
          </label>
          <div class="relative">
            <input
              id="password"
              v-model="password"
              :type="showPassword ? 'text' : 'password'"
              required
              placeholder="Enter your password"
              :class="['input-field pr-10', passwordError && 'border-[#f85149]']"
            />
            <button
              type="button"
              @click="showPassword = !showPassword"
              class="absolute right-3 top-1/2 -translate-y-1/2 text-[#8b949e] hover:text-[#f9f9f9] transition-colors"
            >
              <i :class="showPassword ? 'fa-solid fa-eye-slash' : 'fa-solid fa-eye'" class="w-4 h-4"></i>
            </button>
          </div>
          <p v-if="passwordError" class="mt-1 text-xs text-[#f85149]">{{ passwordError }}</p>
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
const showPassword: Ref<boolean> = ref(false);

/**
 * Error state
 */
const nameError: Ref<string> = ref('');
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
  nameError.value = '';
  emailError.value = '';
  passwordError.value = '';
  generalError.value = '';

  // Validate name
  if (!name.value) {
    nameError.value = 'Please enter your name.';
    return;
  }

  // Validate email
  if (!email.value) {
    emailError.value = 'Please enter your email address.';
    return;
  }
  
  if (!validateEmail(email.value)) {
    emailError.value = 'Invalid email format.';
    return;
  }

  // Validate password
  if (!password.value) {
    passwordError.value = 'Please enter your password.';
    return;
  }

  if (password.value.length < 6) {
    passwordError.value = 'Password must be at least 6 characters long.';
    return;
  }

  // Try to signup
  try {
    await signup({
      name: name.value,
      email: email.value,
      password: password.value
    });
  } catch (error) {
    // Set general error message
    const errorMessage = error instanceof Error ? error.message : 'Signup failed. Please try again.';
    generalError.value = errorMessage;
  }
};
</script>
