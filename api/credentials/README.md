# credentials/

Dossier des clés/secrets **locaux** (dev). Le contenu est **git-ignoré** — seul ce
README est versionné, pour que le dossier existe à la sortie du clone.

## Gmail Postmaster Tools

La réputation Gmail (page **Santé email**) utilise désormais **OAuth par utilisateur** :
chaque compte connecte son Google Postmaster via le bouton dans l'app.

Prérequis côté Google Cloud (une fois pour la plateforme) :

1. Activer l'API **Postmaster Tools**.
2. Ajouter le scope `https://www.googleapis.com/auth/postmaster.traffic.readonly` à
   l'écran de consentement OAuth.
3. Enregistrer l'URI de redirection Postmaster dans les identifiants OAuth :
   `GOOGLE_POSTMASTER_REDIRECT_URI` (défaut local :
   `http://localhost:8000/api/v1/email-health/postmaster/callback`).

Les anciennes variables `GOOGLE_POSTMASTER_CREDENTIALS_*` (service account) ne sont
plus utilisées par l'interface.
