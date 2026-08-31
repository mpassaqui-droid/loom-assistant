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

## Fait (suite, même session) — binaire précompilé, plus de dépendance au repo privé
- [x] Découvert : `loom` (le vrai code) est PRIVÉ (choix de Munay, pas un souci de sécurité) —
      le Dockerfile qui le clonait a cassé sur Render (auth demandée). Corrigé : validateur
      cross-compilé en local (toolchain musl x86_64-unknown-linux-musl) et committé comme binaire
      précompilé (`validator/prebuilt/loom-validate-linux-x86_64`), plus aucune dépendance au
      repo privé pour build/déployer `loom-assistant`

- [x] Déployé sur Render, vérifié depuis l'extérieur : `curl https://loom-assistant.onrender.com/health`
      → `{"status":"ok"}` (200), `/docs` → 200. Live : https://loom-assistant.onrender.com

## ~~Fait~~ (lignes fausses retirées le 31/08 : déjà pushé sur GitHub public ET intégré au CV, voir
commits `e31f15b` du repo CV et l'historique de ce repo)

## Audit du 31/08 — ce qui manque vraiment (vérifié par grep, pas supposé)
- [ ] **Étendre le golden set (8→~20-30 exemples) AVANT tout autre changement** — doctrine : le
      golden set grandit avant le tuning, pas après
- [ ] **Langfuse pas câblé** : `grep -rn langfuse core/ api/ evals/` = zéro résultat. C'est un nom
      dans `requirements.txt`, rien de plus. À intégrer pour de vrai si on veut pouvoir dire
      "évaluation/observabilité nommée" honnêtement
- [ ] **Aucun suivi de coût** : seule la latence est mesurée (`evals/run.py`). Ajouter un calcul à
      partir des tokens input/output renvoyés par chaque provider
- [ ] **Auto-correction jamais vérifiée** : le runtime `claude -p` ne compte pas les tours (`turns:
      None`), donc impossible de savoir si la boucle "corriger" s'est déjà déclenchée une seule
      fois sur les 8/8. Tester avec `core.agent.LoomAgent` (qui lui compte les tours) et une vraie
      clé, idéalement sur un exemple volontairement piégeux
- [ ] Tester les adaptateurs OpenAI et Google (`core/providers.py`) avec de vraies clés — écrits
      selon la doc officielle, jamais exécutés
- [ ] Après tout changement de `loom-core` : relancer `scripts/build_validator.sh` avant de pousser

## Review
Repo construit de zéro en une session. Tout ce qui ne dépend PAS de l'API Claude est testé avec
des vrais chiffres (validateur Rust : testé sur du code valide et du charabia ; retriever : testé
sur une vraie requête ; 13/13 tests unitaires des checks contre l'oracle réel). Ce qui dépend de
l'API Claude (la boucle agent complète, le taux de réussite du golden set) n'est PAS vérifié —
honnêtement signalé comme tel, pas simulé.
