# Images placeholder & fallback par template

> But : garantir qu'un site généré **n'est jamais vide ni sans images**, même pour un prospect
> quasi sans données (peu de texte, ~0 photo). Document d'inventaire + plan de fallback SiteContent.
> Établi le 2026-08-02.

## Le problème (cause racine)

Toutes les images d'un site viennent du `SiteContent`, assemblé côté API par
`map_prospect_and_enrichment` — [`api/services/templates/site_content.py`](../api/services/templates/site_content.py) :

```python
"heroImage": photos[0] if len(photos) > 0 else "",   # ← "" si le prospect n'a pas de photo
"aboutImage": photos[1] if len(photos) > 1 else "",   # ← ""
"gallery":   [{"url": url, "alt": ""} for url in photos[2:]],  # ← [] si < 3 photos
```

`photos` = `enrichment["photos"]` (photos Google scrapées). **Prospect sans photos → hero/about/galerie
vides → site sans images.** Il n'existe aucun fallback à cet endroit.

Côté rendu, les templates **masquent** la section quand l'image manque (`v-if="hasGallery"`,
`v-if="page.gallery.length"`, `v-if="showHeroImage"`), d'où le site « troué ».

## Les emplacements d'image du SiteContent (communs à tous les templates)

| Champ | Rôle | Rempli par l'API aujourd'hui ? |
|---|---|---|
| `logo` | logo / favicon | `enrichment.logo_url` sinon `""` |
| `heroImage` | grande photo d'en-tête | `photos[0]` sinon `""` |
| `aboutImage` | photo section « à propos » | `photos[1]` sinon `""` |
| `gallery[]` | galerie | `photos[2:]` sinon `[]` |
| `beforeAfter[]` | avant/après | **jamais** (toujours `[]`) |

## Deux mécanismes coexistent aujourd'hui (incohérence)

- **Fallback côté layer (OK)** : `dental`, `food`, `barber` embarquent un pool Unsplash dans
  `app/types/<template>.ts` et l'appliquent au rendu quand l'image prospect manque.
  → jamais vides, images libres de droit.
- **Masquage si vide (KO)** : `artisan-edito`, `plumber-signature`, `plumber-atelier`,
  `plumber-cuivre`, `electrician-lumen`, `mechanic-pitlane` n'ont **que** des placeholders dans
  leur mock `.playground` (jamais utilisé en génération réelle) → sections masquées → site troué.

## Inventaire par template (10 live)

| Template | Images actuelles | Type | Verdict fallback | Action |
|---|---|---|---|---|
| **artisan-edito** | `picsum.photos` (hero, about, 6 galerie, 2 avant/après) | URL aléatoire | ❌ placeholder non métier | Sourcer pool générique artisan |
| **plumber-signature** | `picsum.photos` (hero, about, 6 galerie, 2 avant/après) | URL aléatoire | ❌ | Sourcer pool plomberie |
| **plumber-atelier** | `picsum.photos` (hero, about, 6 galerie) | URL aléatoire | ❌ | Pool plomberie (partagé) |
| **plumber-cuivre** | `picsum.photos` (hero, about, 6 galerie) | URL aléatoire | ❌ | Pool plomberie (partagé) |
| **electrician-lumen** | `picsum.photos` (hero, about, 6 galerie) | URL aléatoire | ❌ | Sourcer pool électricité |
| **mechanic-pitlane** | `garagedulandry.com` ×8 + Unsplash ×2 | URL site réel | ⚠️ **droits** — vrai garage | Remplacer par pool garage (2 Unsplash réutilisables) |
| **dental** | pool Unsplash (`app/types/dental.ts`) | URL Unsplash | ✅ déjà bon | Réutiliser tel quel |
| **food** | pool Unsplash (`app/types/food.ts`, vérifiées 200) | URL Unsplash | ✅ déjà bon | Réutiliser tel quel |
| **barber** | pool Unsplash (`app/types/barber.ts`) | URL Unsplash | ✅ déjà bon | Réutiliser tel quel |
| **landscaper-verdure** | 39 fichiers `image-import-*.jpg` (exports Pencil) | Fichiers bundlés | ⚠️ pas de pool URL | Sourcer pool paysagiste |

### Détail des images à remplacer

**`mechanic-pitlane`** — les 8 URLs pointent le site d'un **vrai garage concurrent**
(`garagedulandry.com`), à ne pas expédier sur des sites vendus à d'autres garages :
```
hero      https://www.garagedulandry.com/upload-slider_home/medium1920/slider.jpg
about     https://www.garagedulandry.com/upload-settings/medium800/img-1.jpg
atelier   https://www.garagedulandry.com/upload-bloc_raison/medium1920/bg-centre.jpg
parallax  https://www.garagedulandry.com/sx-content/uploads/cms/medium1920/parallax.jpg
service1  https://www.garagedulandry.com/upload-bloc_service/medium1200/img1.jpg
service2  https://www.garagedulandry.com/upload-bloc_service/medium1200/img2.jpg
service3  https://www.garagedulandry.com/upload-bloc_service/medium1200/services-1-1.jpeg
cat       https://www.garagedulandry.com/upload-categorie_ref_prod/medium640/adobestock-...jpeg
```
Réutilisables (libres de droit, déjà dans le repo) :
```
gallery1  https://images.unsplash.com/photo-1486262715619-67b85e0b08d3?...  (poste de travail)
gallery2  https://images.unsplash.com/photo-1619642751034-765dfdf7c58e?...  (baie de réparation)
```

**`picsum.photos`** (artisan-edito, 3 plombiers, electrician) : images **aléatoires** non liées au
métier — inutilisables comme fallback crédible. À remplacer par des pools Unsplash/Lummi par métier.

## Métiers pour lesquels sourcer un pool royalty-free

Chaque pool = ~1 hero + 1 about + 4–6 galerie (Unsplash ou lummi.ai), format métier.

1. **Plomberie** — partagé par `plumber-signature`, `plumber-atelier`, `plumber-cuivre`.
2. **Électricité** — `electrician-lumen`.
3. **Garage / mécanique** — `mechanic-pitlane` (garde les 2 Unsplash existantes, complète le reste).
4. **Paysagiste / verdure** — `landscaper-verdure`.
5. **Artisan générique multi-métier** — `artisan-edito` (template par défaut).
6. **Déjà couverts (réutiliser)** — dentaire, food, barber.

## Verdict récupération vs sourcing (après fouille de l'historique git)

| Template | Images d'origine dans le repo ? | Décision |
|---|---|---|
| dental | ✅ pool Unsplash (`app/types/dental.ts`) + exports Pencil `image-import-*` | Réutiliser le pool existant |
| food | ✅ pool Unsplash (`app/types/food.ts`) + exports Pencil | Réutiliser le pool existant |
| barber | ✅ pool Unsplash (`app/types/barber.ts`) + exports Pencil | Réutiliser le pool existant |
| landscaper-verdure | ✅ 39 exports Pencil `image-import-*.jpg` (servis dans `public/images/`) | Récupérer les fichiers du repo |
| mechanic-pitlane | ⚠️ `garagedulandry.com` (interdit) + 2 Unsplash réutilisables | Garder les 2 Unsplash, **sourcer** le reste |
| artisan-edito | ❌ **aucune trace** (jamais que `picsum`, 0 fichier en 4 commits) | **Sourcer** (générique artisan) |
| plumber-signature | ❌ aucune trace (picsum seul) | **Sourcer** (pool plomberie) |
| plumber-atelier | ❌ aucune trace (picsum seul) | **Sourcer** (pool plomberie partagé) |
| plumber-cuivre | ❌ aucune trace (picsum seul) | **Sourcer** (pool plomberie partagé) |
| electrician-lumen | ❌ aucune trace (picsum seul) | **Sourcer** (pool électricité) |

Sourcing à faire (Unsplash **et** Lummi.ai comparés, meilleure correspondance retenue) : **artisan générique,
plomberie (1 pool pour 3 templates), électricité, garage**. Paysagiste = récupération des exports Pencil.

## Approche d'implémentation retenue (décidée par Léo)

**Fallback côté layer, dans chaque repo template** : un `SiteContent` **complet** de fallback (texte,
services, FAQ, avis, images, galerie, points forts…) + un **merge clé par clé** — chaque clé du
`SiteContent` reçu qui est **vide** est remplacée par celle du fallback. Un site n'est donc jamais troué.

Par template :
1. Compléter le `defaults` / fallback `SiteContent` du root component pour couvrir **toutes** les clés.
2. Rendre le merge **sensible au vide** (`""`, `[]`) et pas seulement à l'absence de clé.
3. Images : récupérer celles d'origine du repo, sinon sourcer (tableau ci-dessus).
4. Bump de tag → mettre à jour `demo-host/nuxt.config.ts` **et** `api/services/templates/template_repos.py`
   → redeploy demo-host (Vercel, auto sur `main`).

Ordre proposé (priorité vague d'août + risque juridique) : **mechanic-pitlane** (lance + retire
garagedulandry) → **barber** (déjà bon, sert de patron de merge) → plombiers → électricien →
artisan-edito → paysagiste. dental/food/barber : surtout vérifier la complétude du fallback + le merge.
