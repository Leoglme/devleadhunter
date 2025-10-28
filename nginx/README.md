# Configuration Nginx

Ce dossier contient les configurations Nginx pour le déploiement de DevLeadHunter.

## Fichiers

- **nginx-client.conf** : Configuration pour le client Nuxt.js
- **nginx-server.conf** : Configuration pour l'API FastAPI

## Déploiement automatique

### Configuration Client

Le workflow GitHub Actions `.github/workflows/deploy-nginx-client.yml` se déclenche automatiquement lorsque vous modifiez `nginx/nginx-client.conf` et poussez sur la branche `main`.

Le workflow :
1. ✅ Copie le fichier de configuration sur le VPS
2. ✅ Teste la nouvelle configuration (`nginx -t`)
3. ✅ Recharge nginx (`systemctl reload nginx`)
4. ✅ Affiche un résumé de la configuration

### Configuration Serveur API

Le workflow GitHub Actions `.github/workflows/deploy-nginx-server.yml` se déclenche automatiquement lorsque vous modifiez `nginx/nginx-server.conf` et poussez sur la branche `main`.

Le workflow :
1. ✅ Copie le fichier de configuration sur le VPS
2. ✅ Teste la nouvelle configuration (`nginx -t`)
3. ✅ Recharge nginx (`systemctl reload nginx`)
4. ✅ Affiche un résumé de la configuration

### Workflow manuel

Vous pouvez aussi déclencher les workflows manuellement depuis l'onglet "Actions" de GitHub.

## Paths sur le VPS

- Client : `/etc/nginx/sites-enabled/devleadhunter.dibodev.fr`
- Serveur API : `/etc/nginx/sites-enabled/api.devleadhunter.dibodev.fr`

## SSL

Les certificats SSL sont configurés pour être récupérés depuis Let's Encrypt :
- Client : `/etc/letsencrypt/live/devleadhunter.dibodev.fr/`
- Serveur API : `/etc/letsencrypt/live/api.devleadhunter.dibodev.fr/`

Assurez-vous que les certificats sont bien installés avant d'activer les configurations.
