# Pointage assisté (téléphone d'un collègue) et pointage par un manager — Design

Date : 2026-10-26
Dépôts concernés : `backend/` (FastAPI, event sourcing) et `frontend/` (Flutter, app mobile + back-office web).

## 1. Intention

Un employé (Paul) n'a pas son téléphone. Il prend celui d'un collègue (Marie), sur lequel Marie est connectée, et pointe **pour lui-même** en saisissant son matricule et en prenant un **selfie**.

Comme le téléphone n'appartient pas à la personne pointée, ce pointage est suspect par nature. Il crée une **anomalie** qu'un responsable (tout rôle supérieur à EMPLOYEE) valide ou rejette. **Tant qu'il n'est pas validé, ce pointage ne compte pas dans les heures travaillées.**

Second cas, `MANAGER_ASSISTED` : un responsable (rôle > EMPLOYEE) fait pointer un employé depuis la liste des employés, sur son téléphone ou dans le back-office. Ce pointage est de confiance. Il compte immédiatement, sans photo ni validation, et on garde la trace du responsable qui l'a fait.

## 2. Objectifs / non-objectifs / anti-objectifs

**Objectifs**
- Depuis l'app mobile, l'utilisateur connecté peut pointer pour un autre employé identifié par son matricule.
- Le matricule est vérifié avant de pointer. L'app affiche le nom de l'employé trouvé pour confirmation.
- Le selfie est obligatoire et conservé.
- Une anomalie `ASSISTED_POINTING` est créée automatiquement, avec la photo et l'identité de l'utilisateur dont le téléphone a servi.
- Le pointage est exclu du calcul des heures tant qu'il n'est pas validé, et définitivement s'il est rejeté.
- Les rôles MANAGER, HR, PAYROLL et ADMIN peuvent valider ou rejeter depuis le back-office web. On enregistre qui a décidé, quand, et avec quel commentaire.
- La décision déclenche le recalcul de la journée concernée.

**Non-objectifs** (cette itération)
- Pas de reconnaissance faciale ni de comparaison automatique du selfie.
- Pas de périmètre « manager → son équipe » : tout responsable voit et traite toutes les anomalies de pointage assisté. Le modèle n'a pas de lien superviseur, et l'utilisateur a défini « superviseur = tout rôle > EMPLOYEE ».
- Pas de saisie d'une heure arbitraire par le manager : le pointage manager est toujours horodaté à l'instant du clic.
- Pas de notifications (mail/push) aux responsables.
- Ne pas finir le reste du module `adjustements` (demandes de régularisation, etc.) au-delà de ce qui sert ici.

**Anti-objectifs** (ce qui ferait échouer la fonctionnalité même si elle « marche »)
- Un pointage assisté non validé qui apparaît dans les heures payées.
- Un pointage assisté possible sans selfie, ou sans trace du téléphone utilisé.
- Un pointage normal (pour soi-même) rendu plus lent ou plus compliqué.
- Pouvoir pointer pour soi-même via le chemin « assisté » (matricule = celui de l'utilisateur connecté) : refusé.

## 3. Règles métier décidées

| Règle | Décision |
|---|---|
| Qui est la personne pointée | L'employé dont le matricule est saisi (`find_by_employee_number`) |
| Qui est enregistré comme « assistant » | L'utilisateur connecté (le propriétaire du téléphone), à partir du token |
| Photo | Selfie obligatoire, pris par l'appareil photo (pas de galerie) au moment du pointage |
| Règle des 500 m | Appliquée au **site de la personne pointée**, avec le GPS du téléphone utilisé |
| Affectation active | La personne pointée doit avoir une affectation active ce jour-là (même erreur que pour un pointage normal) |
| Entrée ou sortie | Résolue par le serveur sur l'historique de la **personne pointée**. *Choix du concepteur :* l'historique inclut ses pointages en attente, mais pas les rejetés. Un deuxième pointage assisté devient donc bien une SORTIE. |
| Qui valide | Rôle `at_least(MANAGER)` : MANAGER, HR, PAYROLL, ADMIN. Contrôle fait côté route **et** handler. |
| Auto-validation | Un responsable ne peut pas décider d'une anomalie dont il est la personne pointée ou l'assistant. *Choix du concepteur.* |
| Validé | Le pointage compte et la journée est recalculée |
| Rejeté | Le pointage ne compte jamais. Il reste dans l'historique (event sourcing), marqué rejeté. Commentaire obligatoire au rejet. *Choix du concepteur.* |
| Effet d'un rejet sur les pointages suivants | **Décision de l'utilisateur : on accepte le trou.** Le type entrée/sortie des pointages suivants n'est jamais recalculé. Après le rejet, la journée recalculée peut contenir des pointages non appariés, ce qui la passe déjà en `ANOMALY`. Les RH corrigent à la main. |
| Journée déjà validée (`DailyTimeResult` VALIDATED) | La décision est enregistrée, mais le recalcul ne peut pas écraser une journée validée (`DailyTimeResultValidatedError`). On journalise et on laisse la journée telle quelle. *À traiter plus tard si besoin.* |
| Clôture de période | L'anomalie est créée en `BLOCKING`, donc `ClosePeriodHandler` refuse déjà de clôturer une période avec un pointage assisté non traité. |

## 4. Conception technique

### 4.1 Punch (backend/src/punch)
- `TimeEntry` gagne :
  - `assisted_by_user_id: UserId | None` ;
  - `photo_key: str | None` (clé de l'objet dans MinIO) ;
  - `validation_status` : `COUNTED` (défaut, pointage normal) / `PENDING` / `REJECTED`. Un pointage assisté validé devient `COUNTED`.
- Les anciens événements `TimeEntryCreated` doivent se rejouer sans ces champs (valeurs par défaut : `None`, `COUNTED`).
- Les décisions passent par deux nouveaux événements sur le stream du TimeEntry : `TimeEntryValidated` et `TimeEntryRejected`. Ils portent `decided_by` et `decided_at`.
- `source = EntrySource.ASSISTED`. Une nouvelle valeur est ajoutée, parce que `MANAGER_ASSISTED` désigne un autre cas.
- Nouvelle commande `CreateAssistedTimeEntryCommand(actor_user_id, employee_number, location, photo, idempotency_key, wifi_identifier)` et son handler.
  - Le handler réutilise la logique de distance, d'affectation et d'entrée/sortie du handler existant. Il la factorise au lieu de la dupliquer.
- Nouvelle route `POST /time-entries/assisted`, en `multipart/form-data` (champs du pointage + fichier `photo`, JPEG/PNG, 5 Mo max).
- Nouvelle route `GET /employees/lookup?employee_number=...` (ou `GET /time-entries/assisted/lookup`), accessible à tout utilisateur connecté.
  - Elle retourne seulement `{employee_number, first_name, last_name}` de l'employé actif, ou 404.
  - Elle refuse si le matricule est celui de l'utilisateur connecté.
- Le read model `time_entries` gagne les colonnes `assisted_by_user_id`, `photo_key`, `validation_status`. Les mêmes colonnes vont dans `read_model.sql` et dans la projection.

### 4.2 Stockage du selfie
- On utilise MinIO (déjà dans `docker-compose.yml`, encore inutilisé) en API S3 : bucket `punch-photos`, clé `time-entries/{time_entry_id}.jpg`.
- Il faut un client S3 (`boto3` ou `minio`), des paramètres dans `core/settings`, et une abstraction `IPhotoStorage` dans le domaine ou l'application, implémentée dans l'infrastructure.
  - L'abstraction sert aussi aux tests, avec une implémentation en mémoire.
- L'upload a lieu avant l'écriture des événements. Si le commit échoue, l'objet reste orphelin. C'est accepté (pas de nettoyage dans cette itération).
- Lecture : `GET /anomalies/{id}/photo`, réservé à `at_least(MANAGER)`. La route renvoie l'image, soit en flux à travers l'API, soit par une redirection vers une URL présignée courte. Le choix est laissé au builder.

### 4.3 Anomalies (backend/src/adjustements)
- `Anomaly` gagne :
  - `employee_id` (la personne pointée) ;
  - `assisted_by_user_id` ;
  - `decided_by`, `decided_at`, `decision_comment`.
- Elle gagne aussi deux méthodes, `validate(by, comment?)` et `reject(by, comment)`, avec les événements `AnomalyValidated` et `AnomalyRejected`.
  - `AnomalyStatus` gagne `VALIDATED` et `REJECTED`.
  - Seule une anomalie `OPEN` ou `IN_PROGRESS` peut être décidée, sinon erreur de domaine.
- Création : l'anomalie (`type=ASSISTED_POINTING`, `severity=BLOCKING`) est créée **dans la même transaction** que le TimeEntry assisté, par le même handler. C'est le motif inter-contextes de `NeutralizeAnomalyHandler`.
  - *Raison :* un pointage en attente ne doit jamais exister sans son anomalie.
- Une décision fait deux choses dans la même transaction :
  - elle met à jour l'anomalie ;
  - elle émet `TimeEntryValidated` ou `TimeEntryRejected` sur le TimeEntry lié.
- Ensuite elle déclenche le recalcul de la journée de l'employé. Ce peut être un appel direct après commit, ou un consumer outbox. Le choix est laissé au builder, qui suit le motif le plus simple existant.
- Le module a besoin d'un container, de dépendances et d'un routeur, enregistré dans `main.py` :
  - `GET /anomalies?type=&status=&page=` : liste paginée pour le back-office (nom de l'employé pointé, nom de l'assistant, date/heure, entrée/sortie, site, statut) ;
  - `GET /anomalies/{id}` ;
  - `GET /anomalies/{id}/photo` ;
  - `POST /anomalies/{id}/validate` (body `{comment?}`) ;
  - `POST /anomalies/{id}/reject` (body `{comment}`, obligatoire).
  - Toutes ces routes exigent `require_role(MANAGER, HR, PAYROLL, ADMIN)`.
- Le read model `anomalies` gagne les colonnes `employee_id`, `assisted_by_user_id`, `decided_by`, `decided_at`, `decision_comment`.

### 4.4 Calcul des heures (backend/src/time_calculation)
- `TimeCalculationService.calculate_day` ignore les pointages dont `validation_status != COUNTED` au moment de construire la liste des pointages (`time_calculation_service.py:69-72`).
- Effet sur l'anomalie ouverte : comme aujourd'hui, une anomalie `BLOCKING` ouverte met la journée en `BLOCKED`. Elle ne peut donc pas être validée tant que le pointage assisté n'est pas traité, ce qui est voulu.

### 4.5 App mobile (frontend, `main.dart`)
- Sur `PunchScreen`, une action secondaire « Pointer pour un collègue », sous le gros bouton. Le bouton principal reste inchangé.
- Le parcours :
  1. L'utilisateur saisit le matricule, puis touche « Vérifier ». L'app appelle le lookup.
  2. L'app affiche « Nom Prénom » et un bouton « C'est moi ». Un matricule inconnu donne un message d'erreur.
  3. Écran selfie : caméra frontale, avec possibilité de reprendre la photo.
  4. Envoi multipart vers `/time-entries/assisted` avec le GPS.
  5. Confirmation : « Pointage enregistré pour X — en attente de validation ».
- Après l'envoi, on revient à l'écran normal. La session de Marie reste active et l'état « dernier pointage » de Marie n'est pas modifié.
- Nouvelle dépendance pour la caméra : `image_picker` (caméra frontale forcée) ou `camera`. Le choix est laissé au builder. Il faut aussi les permissions Android/iOS correspondantes.

### 4.6 Back-office web (frontend, `main_admin.dart`)
- Un nouveau menu « Anomalies » dans `AdminShell`.
  - Il affiche une liste filtrable par statut (défaut : ouvertes), avec les colonnes employé pointé, assistant (téléphone de), date/heure, entrée/sortie, site, statut.
  - Il suit les conventions des écrans Employés : table desktop et cartes mobiles.
- Le détail montre :
  - le selfie, en grand ;
  - les infos du pointage ;
  - les boutons **Valider** et **Rejeter**. Rejeter ouvre un champ commentaire obligatoire.
- Après la décision, la liste est rafraîchie.

### 4.7 Pointage par un manager (`MANAGER_ASSISTED`)
**Règles (décisions de l'utilisateur)**
- Le pointage se fait depuis le téléphone du manager ou le back-office web, à partir de la liste des employés, avec un bouton « Faire pointer » sur chaque employé.
- L'heure enregistrée est **l'heure serveur au moment du clic**. Aucune saisie d'heure n'est possible.
- Pas de photo, pas d'anomalie, pas de validation : `validation_status = COUNTED` dès la création.
- On enregistre le responsable dans `assisted_by_user_id`.
- Entrée ou sortie : le serveur la résout sur l'historique de l'employé, comme pour un pointage normal.

**Choix du concepteur**
- Rôles autorisés : `at_least(MANAGER)`, donc les mêmes que pour la validation. Pas de périmètre d'équipe : tous les employés actifs sont concernés.
- Interdit sur soi-même : un responsable ne pointe pas pour lui-même via ce bouton.
- Pas de contrôle GPS ni de règle des 500 m, puisque le manager peut être au back-office hors site. `location` reste nul et `location_confidence` vaut LOW. L'affectation active du jour reste exigée.

**Backend**
- Nouvelle commande `CreateManagerTimeEntryCommand(actor_user_id, employee_id, idempotency_key)` et son handler, qui réutilise la résolution entrée/sortie et la vérification d'affectation.
- Nouvelle route `POST /employees/{employee_id}/time-entries`, protégée par `require_role(MANAGER, HR, PAYROLL, ADMIN)`.
  - Elle répond avec le pointage créé, dont son type entrée/sortie, pour que l'interface affiche « Entrée enregistrée pour X à 08:02 ».
- Le contrôle de rôle est fait aussi dans le handler.

**Back-office web**
- Un bouton « Faire pointer » sur chaque ligne ou carte de l'écran Employés existant, et sur la fiche employé.
- Une confirmation est demandée avant l'envoi : « Faire pointer X maintenant ? ».

**App mobile**
- Si le rôle de l'utilisateur est au moins MANAGER, un accès « Employés » apparaît en plus de l'écran de pointage. Il peut passer par le `MobileShell` existant mais inutilisé, ou par un bouton. Le choix est laissé au builder.
- Cet accès donne une liste avec recherche (nom, matricule), le bouton « Faire pointer » et la même confirmation. On réutilise si possible les widgets responsives des écrans Employés (cartes).
- Le pointage personnel du manager reste inchangé.

**Tests**
- Création OK, avec un type entrée/sortie correct.
- 403 pour EMPLOYEE, refus sur soi-même, refus si l'employé n'a pas d'affectation.
- Le pointage compte immédiatement dans `calculate_day`.

## 5. Tests attendus
- **Domaine**
  - `TimeEntry` assisté : les états et le rejeu fonctionnent, et les anciens événements se rejouent sans les nouveaux champs.
  - `Anomaly.validate` et `Anomaly.reject` respectent les transitions interdites.
  - Le calculateur ignore les pointages `PENDING` et `REJECTED`.
- **API** (motif `tests/identity` : repos en mémoire + TestClient)
  - Pointage assisté OK.
  - Cas refusés : matricule inconnu, son propre matricule, photo absente, hors zone, sans affectation.
  - validate/reject : 403 pour EMPLOYEE, 403 pour l'auto-validation, 409 si déjà décidée.
- **Frontend** : tests unitaires du controller du parcours assisté et test widget de l'écran de décision, avec les helpers `test/helpers`.

## 6. Laissé au builder
- Le nom exact des routes et des classes, en suivant les conventions du module.
- Le flux photo : passage par l'API ou URL présignée.
- Le mécanisme de recalcul après décision : appel direct ou consumer outbox.
- Le package caméra Flutter.
- Le découpage en tâches et l'ordre d'implémentation entre les deux dépôts.
