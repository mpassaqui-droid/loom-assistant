# Leçons — loom-assistant

---

# loom-core::parse() ne renvoie jamais d'erreur
lesson: le parseur LOOM est permissif à défauts silencieux (`.unwrap_or(défaut)` partout, testé
empiriquement sur du charabia total → 0 voix, jamais de panique/erreur). "Ça parse" n'est donc pas
une métrique d'éval valable — il faut vérifier le comportement réel planifié (`schedule_bar`)
contre l'intention sémantique du prompt, pas juste l'acceptation syntaxique.

# Les gros exemples .loom dépassent le contexte d'embedding
lesson: certains fichiers `.loom` d'exemple font 6000+ caractères, au-delà du contexte du modèle
d'embedding. Solution : tronquer le texte envoyé à l'embedding tout en gardant le texte complet
original pour l'affichage/citation — le vecteur reste suffisamment représentatif pour un langage
aussi dense que LOOM.

# Ne jamais supposer qu'un repo compagnon est public
lesson: j'ai construit un Dockerfile qui clonait `github.com/mpassaqui-droid/loom` en supposant
qu'il était public (je l'ai confondu avec `loom-showcase`, qui lui l'est). `loom` est PRIVÉ par
choix explicite de Munay (protéger ses idées, pas un souci de sécurité). Le build a échoué sur
Render avec une demande d'authentification git — ce qui a révélé l'hypothèse fausse. Toujours
vérifier la visibilité réelle (`gh repo view --json visibility`) avant de bâtir une dépendance de
build sur un repo qu'on suppose public.

# Ollama pour les embeddings = mauvais choix pour un déploiement gratuit
lesson: Ollama exige un serveur séparé qui tourne en continu — pas garanti de tenir sur un hébergeur
gratuit (Render/Railway). Remplacé par `fastembed` (ONNX, pas de PyTorch, tourne dans le process
Python lui-même, ~130 Mo) : zéro serveur à héberger, marche pareil en local et en prod. Toujours
préférer un modèle qui tourne IN-PROCESS à un modèle qui exige un service à part, quand la cible
de déploiement est un tier gratuit.
