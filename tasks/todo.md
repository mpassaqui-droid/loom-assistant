# To-do — loom-assistant

## Fait (session du 31/08/2026)
- [x] Validateur Rust (`validator/`) qui appelle le vrai `loom-core::parse()` + `schedule_bar_seeded()`
- [x] RAG hybride (Chroma + BM25 + RRF) sur les docs et 62 exemples LOOM — 104 chunks indexés
- [x] Boucle agent (`core/agent.py`, tools chercher_docs + valider_loom) — code écrit, PAS testé en vrai (pas de ANTHROPIC_API_KEY dans ce sandbox)
- [x] 8 exemples golden set + 5 fonctions de check contre le vrai oracle — 13/13 tests unitaires passent
- [x] API FastAPI (`/ask`, `/health`), rate limit basique
- [x] Dockerfile + docker-compose.yml (avec sidecar Ollama)

## Fait (suite, même session) — débloqué via `claude -p`
- [x] `core/agent_cli.py` : même interface que `core.agent.LoomAgent`, mais via `claude -p
      --allowedTools Bash` (abonnement Max, zéro clé API) — pour tester en local seulement,
      jamais pour la démo publique déployée (une session perso n'a pas vocation à servir du
      trafic public, cf. docstring du fichier)
- [x] Golden set (8 exemples) lancé pour de vrai via ce runtime : **8/8 (100%)**, latence
      p50=17.6s / p95=27.2s — latence gonflée par le démarrage d'une session Claude Code à
      chaque appel (pas représentative de l'API en prod, qui répondrait en 2-5s)

## Fait (suite, même session) — Ollama viré, BYOK multi-provider
- [x] Embeddings basculés sur `fastembed` (ONNX, in-process, ~130 Mo) — plus de serveur Ollama à
      héberger, résout le vrai blocage de déploiement gratuit. Réindexé (104 chunks), retriever
      re-testé sur une vraie requête, 13/13 tests toujours verts.
- [x] `core/providers.py` : bring-your-own-key, Anthropic/OpenAI/Google — chaque visiteur de la
      démo apporte sa clé, jamais stockée/loggée. Seul Anthropic testé en vrai (8/8 golden set via
      `claude -p`) ; OpenAI/Google écrits selon la doc officielle, PAS testés (pas de clé dispo)

## À faire (Munay)
- [ ] Pour la démo publique déployée (Phase 6) : lancer `python3 -m evals.run --runtime api
      --provider anthropic` (ou openai/google) avec une vraie clé pour des chiffres de latence
      représentatifs de prod
- [ ] Décider : Render ou Railway pour le déploiement (plus de blocage Ollama, choix libre maintenant)
- [ ] Étendre le golden set au-delà de 8 exemples avant tout tuning (doctrine : le golden set
      grandit AVANT le changement)
- [ ] git push vers un nouveau repo GitHub public `loom-assistant`
- [ ] Intégrer au CV (`project_cv_ameliorations_template_baswe`) une fois les vrais chiffres obtenus

## Review
Repo construit de zéro en une session. Tout ce qui ne dépend PAS de l'API Claude est testé avec
des vrais chiffres (validateur Rust : testé sur du code valide et du charabia ; retriever : testé
sur une vraie requête ; 13/13 tests unitaires des checks contre l'oracle réel). Ce qui dépend de
l'API Claude (la boucle agent complète, le taux de réussite du golden set) n'est PAS vérifié —
honnêtement signalé comme tel, pas simulé.
