<template>
  <div class="mx-auto max-w-2xl space-y-8">
    <div>
      <h1 class="text-3xl font-bold text-[var(--app-ink)]">Facturation & paiement</h1>
      <p class="text-muted mt-2 text-sm leading-relaxed">
        Connectez le compte qui émettra vos factures et encaissera vos ventes. Toute la facturation passe par lui — vos
        ventes n'existent pas dans DevLeadHunter.
      </p>
    </div>

    <PaymentProviderConfig />
  </div>
</template>

<script lang="ts" setup>
definePageMeta({ layout: 'dashboard', middleware: 'auth' })
</script>
