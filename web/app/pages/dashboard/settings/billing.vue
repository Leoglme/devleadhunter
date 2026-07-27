<template>
  <div class="max-w-3xl space-y-5">
    <div>
      <p class="app-label flex items-center gap-2">
        <LandingAsterisk class="text-[0.6rem] text-[var(--app-accent)]" />
        Compte
      </p>
      <h1 class="app-page-title mt-2">Facturation &amp; paiement</h1>
      <p class="mt-1.5 max-w-2xl text-sm leading-relaxed text-[var(--app-ink-soft)]">
        Connectez le compte qui émettra vos factures et encaissera vos ventes. DevLeadHunter ne touche jamais l'argent :
        tout passe par votre propre compte.
      </p>
    </div>

    <PaymentProviderConfig />
  </div>
</template>

<script lang="ts" setup>
definePageMeta({ layout: 'dashboard', middleware: 'auth' })
</script>
