<template>
  <div class="mx-auto max-w-2xl space-y-8">
    <div>
      <h1 class="text-3xl font-bold text-[var(--app-ink)]">Facturation & paiement</h1>
      <p class="text-muted mt-2 text-sm leading-relaxed">
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
