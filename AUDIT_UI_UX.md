# Audit UI/UX — DevLeadHunter (app dashboard, port 1420)

**TLDR : la base est très saine.** La DA Atelier est cohérente dans les deux thèmes, les drawers persistants marchent bien, la palette Ctrl+K, la carte choroplèthe et la page Santé email sont d'un très bon niveau. Les vrais problèmes sont concentrés sur 3 zones : **des métriques email fausses à l'écran** (200 %, 600 % d'ouverture), **un flash noir à chaque navigation**, et **des parcours qui perdent l'utilisateur autour du wizard** (création de site vs automatisation, validation silencieuse, brouillon perdu). Rien de structurel — beaucoup de corrections à fort impact et faible coût.

⚠️ **Avertissement d'abord** : pendant l'audit, le working tree a été modifié sous mes pieds (11 fichiers — `Sidebar.vue`, `DrawerStackHost.vue`, `ProspectDrawer.vue`, `settingsNav.ts`…, alors que le statut git était propre au départ). Une autre session travaille visiblement sur le repo en ce moment. J'ai vu le menu Paramètres dans deux versions différentes à cause de ça ; j'ai écarté ces faux positifs, mais certains points ci-dessous touchent peut-être un chantier en cours.

---

## 🔴 Priorité 1 — bugs et chiffres faux visibles

**1. Les KPIs email sont incohérents à l'écran.** C'est le problème le plus grave car il détruit la confiance dans l'outil :
- Campagne : « Taux ouv. **200 %** », « Délivrés 1 » mais « Ouverts 2 »
- Suivi des emails : « Envoyés **0** » alors que 10 emails sont partis, « Taux ouv. **600 %** »
- Campagnes (liste) : « Ouverture moyenne 100 % », carte « 200 % »

Deux causes qui se cumulent : les compteurs comptent le **statut courant** (un email passé à « ouvert » ne compte plus dans « envoyés » ni « délivrés »), et les ouvertures sont comptées en **événements** (plusieurs ouvertures du même destinataire). Recommandation : compteurs cumulatifs (un email ouvert est aussi envoyé et délivré), taux d'ouverture = **ouvreurs uniques / délivrés**, plafonné à 100 %. À corriger avant la 1ʳᵉ vague — c'est le tableau de bord avec lequel tu vas juger ta campagne d'août.

**2. Flash noir à chaque navigation.** Chaque changement de page affiche un écran 100 % noir (jusqu'à 2-3 s en dev, la carte de prospection est la pire). Cause trouvée : [main.css:13](web/app/assets/css/main.css:13) — `body { bg-[#050505] }` global (vestige de la landing sombre). En thème clair, c'est violent. Fix : body sur `var(--app-bg)` scopé app + un `NuxtLoadingIndicator` fin en haut.

**3. Page 404 par défaut de Nuxt** (bleu nuit, anglais, « Go back home ») — `/dashboard/settings` y mène d'ailleurs depuis l'historique. Une page d'erreur Atelier en français manque.

**4. Palette Ctrl+K : Entrée ne déclenche rien.** Le footer dit « Entrée ouvrir », mais Entrée (même après ↑↓) n'a rien exécuté dans mes tests — seul le clic marche. À revérifier à la main au clavier réel, mais si ça se confirme, la palette perd la moitié de son intérêt.

**5. Wizard étape 3 : validation silencieuse.** « Continuer » sans Modèle A ne fait strictement rien — pas de message, pas de champ en rouge, pas de toast. L'utilisateur croit que le bouton est cassé.

**6. Campagne → onglet Prospects : colonne « Variante » à « — »** alors que l'onglet File d'attente connaît la variante de chacun (J1 A / J1 B). Donnée présente, affichage cassé.

---

## 🟠 Priorité 2 — parcours et logique

**7. « Créer un site » mène à « Créer une automatisation ».** [create.vue](web/app/pages/dashboard/demo-sites/create.vue) redirige volontairement vers le wizard — OK sur le fond, mais l'utilisateur qui a cliqué « Lancer le builder » atterrit sur un écran titré « Créer une automatisation », breadcrumb « ← Automatisations », sidebar surlignée « Sites démo ». Trois signaux contradictoires. Suggestion : quand on arrive avec l'intention « site », adapter titre/breadcrumb et pré-décocher « Démarcher les prospects par email » à l'étape 3.

**8. Aucun chemin « prospect → générer son site » depuis le drawer prospect.** Les actions sont : contacté, campagne, email, modifier, supprimer, vendu, réserver. Or c'est LE geste central du produit. Un bouton « Générer un site démo » (qui ouvre le wizard pré-rempli avec ce prospect) manque.

**9. Quitter le wizard perd tout, silencieusement.** J'ai configuré 4 étapes, cliqué le breadcrumb retour : aucun avertissement, brouillon perdu. Garde-fou (« Quitter ? Ta configuration sera perdue ») ou autosave du brouillon.

**10. Récapitulatif (étape 4) trop maigre.** « CIBLE : 1 prospect(s) », « DÉMARCHAGE : Modèle A » — on vérifie quoi, au juste ? Afficher les noms des prospects, le nom du template email, la cadence effective. C'est l'écran de confiance avant lancement.

**11. La cadence affichée ment.** La page campagne montre « 1 email toutes les 20 min → **~72 emails/jour** » alors que ta SendPolicy plafonne à 20/jour, Lun-Ven, 7h-18h. Le chemin legacy `send_delay_minutes` est mis en avant avec un calcul théorique faux en pratique. Afficher la policy effective (« Suit tes réglages d'envoi : max 20/j… ») et reléguer l'espacement en avancé.

**13. Mise en route : stepper non cliquable, pas de « Passer ».** Pour revoir l'étape Encaissement, il faut réenregistrer les étapes 1-2-3. Rendre cliquables les étapes complétées (elles ont déjà l'état ✓). Le tile 5 « C'est prêt » est aussi visuellement collé au 4 à largeur moyenne.

**14. Choix d'un modèle d'email à l'aveugle.** Dans le wizard comme en campagne : un `<select>` natif de 18 options, et une fois choisi, seul l'objet s'affiche (« Objet : votre fiche »). Le corps n'est visible nulle part au moment du choix. Un bouton « aperçu » à côté du select (réutilisant le drawer de preview existant) suffirait.

**15. Éditeur de modèle : HTML brut sans aperçu intégré.** On édite `<p>{salutation},</p>…` dans un textarea ; l'aperçu est une action séparée (fermer l'éditeur, cliquer l'œil). Un toggle Écrire/Aperçu dans le drawer d'édition changerait la vie — c'est l'outil de travail du copy, ton levier n°1.

**16. Vidéo de prospection : clip « Prêt » mais invisible.** Aucun player, aucune durée, aucune vignette du clip courant. Impossible de vérifier ce que les prospects verront sans fouiller. Ajouter un lecteur + « Remplacer le clip ».

---

## 🟡 Priorité 3 — cohérence UI

**17. Tailles de titres de pages incohérentes** (vérifié dans le code) : 9 pages en `text-xl`, 3 en `text-2xl`, 8 en `text-3xl`. Même niveau hiérarchique, trois échelles. Idem pour le kicker (● PILOTAGE / ● PROSPECTION) : présent sur certaines pages, absent sur Ventes/Suivi des emails, et Santé email porte « CAMPAGNES » alors qu'elle vit dans Paramètres. À standardiser (le pattern kicker + titre de la home est le plus abouti).

**18. Comptabilité : page 100 % anglaise et hors DA** (« Accounting », « Total received », icônes pastel vert/rose). Vestige pré-refonte. Admin-only donc pas urgent, mais c'est la seule page qui casse l'ensemble.

**19. Téléphones cassés sur deux lignes** dans toutes les tables (« 06 52 57 26 / 94 »). `whitespace-nowrap` + `tabular-nums` sur ces colonnes.

**20. La barre flottante « Continuer » du wizard recouvre la dernière ligne du tableau** de prospects (une ligne entière passe dessous). Padding-bottom sur la liste à hauteur de la barre.

**21. Reflow drawer-ouvert perfectible.** Le socle container-queries marche, mais : le titre wrappe en 3 lignes (« Suivi / des / emails »), et la liste des modèles d'email compressée tronque les titres à « ★ Recomm... » tout en gardant 5 icônes d'action par ligne. En mode compressé, réduire les **actions** (menu ⋮), jamais le titre.

**22. Modèles d'email : 17 poubelles rouges à l'écran.** L'action destructrice est l'élément le plus saillant de la page. La page Utilisateurs fait déjà mieux (menu ⋮ par ligne) — appliquer le même pattern : œil + éditer visibles, dupliquer/archiver/supprimer dans le ⋮.

**23. Mes prospects : hiérarchie des boutons d'en-tête inversée.** Le CTA primaire « Nouvelle recherche » (noir) passe en 2ᵉ ligne sous Actualiser/Importer et chevauche le sous-titre. Le primaire devrait être en 1ʳᵉ position à droite.

**24. Templates de site : aperçus abstraits.** Le picker montre des blocs colorés génériques alors que tu as 9 vraies templates magnifiques. De vraies captures (même statiques, régénérées au tag) rendraient le choix immédiat — et c'est aussi ce que verrait un futur utilisateur payant. Les champs couleur sont du hex texte brut sans color picker (`<input type="color">` natif suffirait).

**25. Détails data qui font désordre** : doublons dans la liste de zone de la carte (« Dugué Chauffage » ×2, « EC Thermie » ×2 — dédup au scraping à prévoir) ; lignes Ventes nommées « #10 », « #9 » quand la commande n'a pas de client (fallback « Commande #10 — sans contact ») ; compteurs « Pas contacté 42 / Contacté 2 » qui ne parlent que des 44 filtrés alors que le KPI au-dessus dit 60 prospects.

---

## ✅ Ce qui est déjà très bon (à ne pas toucher)

Santé email est la meilleure page de l'app (pédagogie, seuils, verdicts « SAIN ») — c'est le niveau à viser partout. Le formulaire « Trouver des prospects » (chips métier, garde-fous cochés, « Comment ça marche ») est exemplaire. Confirmation de suppression propre et nominative. Facturation & paiement (cartes Qonto/Stripe) très réussie. Carte de prospection lisible et agréable. Dark mode globalement irréprochable (vérifié au DOM — l'artefact de sidebar claire sur mes captures venait de l'outil de capture, pas de l'app). Responsive mobile propre.

**Non testé volontairement** (effets de bord) : lancement réel d'une recherche/automatisation, envois d'emails, connexions OAuth, déconnexion, achat de crédits.

**PostHog** : rien à ajouter — le dashboard n'est volontairement pas tracké (décision explicite), et rien dans cet audit ne touche les surfaces trackées.

**Mon top 5 si tu dois choisir avant la vague d'août** : #1 métriques email, #2 flash noir, #5 validation silencieuse du wizard, #11 cadence mensongère, #16 aperçu du clip vidéo — les cinq touchent directement la confiance dans le tunnel que tu t'apprêtes à utiliser en réel.