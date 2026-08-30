# To-do — loom-assistant

## Fait (session du 31/08/2026)
- [x] Validateur Rust (`validator/`) qui appelle le vrai `loom-core::parse()` + `schedule_bar_seeded()`
- [x] RAG hybride (Chroma + BM25 + RRF) sur les docs et 62 exemples LOOM — 104 chunks indexés
- [x] Boucle agent (`core/agent.py`, tools chercher_docs + valider_loom) — code écrit, PAS testé en vrai (pas de ANTHROPIC_API_KEY dans ce sandbox)
- [x] 8 exemples golden set + 5 fonctions de check contre le vrai oracle — 13/13 tests unitaires passent
- [x] API FastAPI (`/ask`, `/health`), rate limit basique
- [x] Dockerfile + docker-compose.yml (avec sidecar Ollama)

## À faire (Munay, avec une vraie clé API)
- [ ] Lancer `python3 -m evals.run` avec `ANTHROPIC_API_KEY` réel, rapporter le vrai taux de
      réussite sémantique (actuellement ZÉRO chiffre réel côté agent, seulement côté validateur/tests)
- [ ] Vérifier que le retriever tourne bien avec Ollama local (`nomic-embed-text` déjà tiré)
- [ ] Décider : déploiement Render/Railway, et si Ollama tient sur le tier gratuit ou s'il faut
      basculer `core/rag.py::_embed` sur une API d'embeddings hébergée
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
