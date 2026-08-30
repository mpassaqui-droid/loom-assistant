# Leçons — loom-assistant

---

# loom-core::parse() ne renvoie jamais d'erreur
lesson: le parseur LOOM est permissif à défauts silencieux (`.unwrap_or(défaut)` partout, testé
empiriquement sur du charabia total → 0 voix, jamais de panique/erreur). "Ça parse" n'est donc pas
une métrique d'éval valable — il faut vérifier le comportement réel planifié (`schedule_bar`)
contre l'intention sémantique du prompt, pas juste l'acceptation syntaxique.

# Les gros exemples .loom dépassent le contexte d'embedding d'Ollama
lesson: certains fichiers `.loom` d'exemple font 6000+ caractères, au-delà du contexte par défaut
de `nomic-embed-text` sur Ollama. Solution : tronquer le texte envoyé à l'embedding (4000 car.)
tout en gardant le texte complet original pour l'affichage/citation — le vecteur reste
suffisamment représentatif pour un langage aussi dense que LOOM.
