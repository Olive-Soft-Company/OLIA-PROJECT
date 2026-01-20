# Analyse Technique et Solution - 404 OAuth Callback Atlassian

## 1. Analyse Technique des Fichiers

### `backend/open_webui/routers/jira_oauth.py`

**Responsabilité:**
- Routeur FastAPI pour le callback OAuth Atlassian/Jira
- Gère la réception des redirections depuis Atlassian après autorisation
- Échange le code d'autorisation contre des tokens
- Stocke les tokens sur disque pour l'utilisateur

**Route déclarée:**
```python
@router.get("/atlassian/callback", response_class=HTMLResponse)
async def atlassian_oauth_callback(request: Request)
```

**Chemin exposé par le routeur:**
- Route relative: `/atlassian/callback`
- **Chemin final dépend du préfixe lors de l'inclusion dans l'app**

**Flux OAuth implémenté:**
1. **Réception du callback** → Lit `code` et `state` depuis query params
2. **Validation redirect_uri** → Compare avec `ATLASSIAN_REDIRECT_URI`
3. **Identification utilisateur** → Depuis session ou depuis `state` (format: `{user_key}:{uuid}`)
4. **Échange code → token** → Appelle `complete_oauth_flow(code)` depuis `jira_oauth.py`
5. **Stockage** → Appelle `set_user_record(user_key, record)`
6. **Réponse HTML** → Page de succès/échec

**Gestion des paramètres:**
- `redirect_uri`: Validé contre `ATLASSIAN_REDIRECT_URI` env var (lignes 73-83)
- `state`: Format `{user_key}:{uuid}`, extrait user_key si session absente (lignes 54-57, 85-120)
- `code`: Échangé contre token via `complete_oauth_flow()` (ligne 123)
- `tokens`: Stockés via `set_user_record()` dans `/data/openwebui/jira_oauth/user_{safe_key}.json`

### `backend/open_webui/utils/jira_oauth.py`

**Responsabilité:**
- Utilitaires OAuth pour Atlassian (client OAuth, échange de tokens, stockage)
- Classe `AtlassianOAuthClient` pour les appels API Atlassian
- Fonction `complete_oauth_flow()` qui orchestre: échange code→token → récupération ressources → construction record

**Fonctions principales:**
- `AtlassianOAuthClient.exchange_code_for_token(code)` → Échange code contre access_token + refresh_token
- `AtlassianOAuthClient.get_accessible_resources(access_token)` → Récupère les ressources Jira accessibles
- `complete_oauth_flow(code)` → Orchestre le flux complet et retourne un record avec `cloud_id`, `cloud_url`, `resource_name`
- `set_user_record(user_key, record)` → Stocke sur disque

## 2. Analyse du Problème 404

### URL de redirection Atlassian:
```
https://olia-ppd.francecentral.cloudapp.azure.com/api/oauth/atlassian/callback
```

### État actuel du code:

**Dans `main.py`:**
- ❌ Le module `jira_oauth` **n'est PAS importé** (lignes 70-96)
- ❌ Le routeur `jira_oauth.router` **n'est PAS inclus** dans l'application FastAPI
- ✅ D'autres routeurs sont inclus avec des préfixes `/api/v1/...`

**Dans `routers/jira_oauth.py`:**
- ✅ Route définie: `@router.get("/atlassian/callback")`
- ✅ Routeur créé: `router = APIRouter()`

### Cause racine du 404:

**Le routeur n'est jamais enregistré dans l'application FastAPI.**

FastAPI ne connaît pas l'existence de cette route car:
1. Le module n'est pas importé dans `main.py`
2. `app.include_router(jira_oauth.router, ...)` n'est jamais appelé

Par conséquent, quand Atlassian redirige vers `/api/oauth/atlassian/callback`, FastAPI retourne 404 car aucune route ne correspond.

## 3. Solution - Modifications Requises

### Étape 1: Ajouter l'import dans `main.py`

**Localisation:** Après la ligne 95 (dans la section des imports de routers)

```python
from open_webui.routers import (
    audio,
    images,
    ollama,
    openai,
    retrieval,
    pipelines,
    tasks,
    auths,
    channels,
    chats,
    notes,
    folders,
    configs,
    groups,
    files,
    functions,
    memories,
    models,
    knowledge,
    prompts,
    evaluations,
    tools,
    users,
    utils,
    scim,
    jira_oauth,  # ← AJOUTER CETTE LIGNE
)
```

### Étape 2: Inclure le routeur dans l'application

**Localisation:** Après la ligne 1402 (après `app.include_router(utils.router, ...)`)

```python
app.include_router(utils.router, prefix="/api/v1/utils", tags=["utils"])

# Jira OAuth callback endpoint
app.include_router(jira_oauth.router, prefix="/api/oauth", tags=["jira_oauth"])
```

### Résultat attendu:

Après ces modifications, le chemin final sera:
- **Préfixe:** `/api/oauth`
- **Route:** `/atlassian/callback`
- **Chemin complet:** `/api/oauth/atlassian/callback` ✅

Cela correspond exactement à l'URL de redirection configurée dans Atlassian.

## 4. Code Complet des Modifications

### Fichier: `backend/open_webui/main.py`

**Modification 1 - Ajouter l'import (ligne ~96):**

```python
from open_webui.routers import (
    # ... existing imports ...
    jira_oauth,  # Add this line
)
```

**Modification 2 - Inclure le routeur (après ligne 1402):**

```python
app.include_router(utils.router, prefix="/api/v1/utils", tags=["utils"])

# Jira OAuth callback endpoint
app.include_router(jira_oauth.router, prefix="/api/oauth", tags=["jira_oauth"])
```

## 5. Vérifications Post-Fix

### Vérifier que la route existe:

Après redémarrage de l'application, vérifier:
```bash
# Option 1: Via les logs au démarrage
# FastAPI affichera toutes les routes enregistrées

# Option 2: Via /docs (si ENV=dev)
# Accéder à http://your-domain/docs et chercher "jira_oauth"

# Option 3: Test direct
curl -I https://olia-ppd.francecentral.cloudapp.azure.com/api/oauth/atlassian/callback
# Devrait retourner 400 (paramètres manquants) au lieu de 404
```

### Vérifier la configuration Atlassian:

Dans Atlassian Developer Console, l'URL de callback doit être exactement:
```
https://olia-ppd.francecentral.cloudapp.azure.com/api/oauth/atlassian/callback
```

### Variables d'environnement requises:

```bash
ATLASSIAN_CLIENT_ID=HCmUNO8AAq4iy1OLPDC8S6sG1IU0NbtL
ATLASSIAN_CLIENT_SECRET=<your-secret>
ATLASSIAN_REDIRECT_URI=https://olia-ppd.francecentral.cloudapp.azure.com/api/oauth/atlassian/callback
ATLASSIAN_SCOPES=read:jira-work write:jira-work offline_access
ATLASSIAN_AUDIENCE=api.atlassian.com
# Optionnel:
ATLASSIAN_POST_AUTH_REDIRECT=https://olia-ppd.francecentral.cloudapp.azure.com/
```

## 6. Résumé

**Problème:** 404 Not Found sur `/api/oauth/atlassian/callback`

**Cause:** Routeur `jira_oauth` non importé et non inclus dans l'application FastAPI

**Solution:** 
1. Ajouter `jira_oauth` dans les imports de `main.py`
2. Ajouter `app.include_router(jira_oauth.router, prefix="/api/oauth", tags=["jira_oauth"])`

**URL finale attendue:** `/api/oauth/atlassian/callback` ✅

**Aucune modification nécessaire dans:**
- `routers/jira_oauth.py` (déjà correct)
- `utils/jira_oauth.py` (déjà correct)
- Configuration Atlassian (déjà correcte)

