# Actions sur les employés : modifier, désactiver/réactiver, affecter, plusieurs entreprises — Design

Date : 2026-10-31
Dépôts : `backend/` (FastAPI, event sourcing) et `frontend/` (Flutter : app mobile + back-office web), branche de base `feature/employee-screens`.

## 1. Intention

Depuis la fiche d'un employé, un responsable doit pouvoir :
- **modifier** ses informations ;
- le **désactiver** (congé, départ) puis le **réactiver** ;
- l'**affecter à un site**, maintenant ou à une date future, comme une mutation.

Une même personne peut être employée dans **plusieurs entreprises**. Une entreprise est un **annuaire** (directory). La personne a alors un seul compte, mais une fiche employé par entreprise, chacune avec son propre matricule et éventuellement son propre rôle. Il faut donc pouvoir rattacher un compte existant à une nouvelle entreprise. Il faut aussi, à la connexion, choisir l'entreprise dans laquelle on travaille.

Aujourd'hui :
- `PATCH /employees/{id}` existe mais ne fait rien (le corps est commenté).
- `DeactivateUserHandler` existe mais n'a pas de route.
- Les routes d'affectation existent mais n'ont aucun contrôle de rôle et refusent les chevauchements.
- L'onboarding refuse un email déjà enregistré.
- Le jeton porte le rôle du **compte**, pas celui d'une fiche employé.
- Le pointage normal ne vérifie pas que la fiche est active.

## 2. Objectifs, non-objectifs, anti-objectifs

**Objectifs**
- Modifier depuis la fiche le **nom** (prénom, nom), le **téléphone** et le **rôle**.
- Désactiver et réactiver une fiche employé.
- Affecter un employé à un site à une date du jour ou future. L'affectation en cours s'arrête automatiquement **la veille**.
- Rattacher un compte existant (même email) à une autre entreprise, avec un autre matricule et éventuellement un autre rôle.
- À la connexion par email, si la personne a des fiches actives dans plusieurs entreprises, lui demander laquelle choisir. La session porte alors cette fiche et son rôle.

**Non-objectifs (cette itération)**
- Pas de motif structuré (congé / départ) ni de dates de désactivation. La désactivation est un simple interrupteur. Les congés planifiés relèvent du module absences.
- Pas de périmètre « un manager ne gère que son entreprise » : comme aujourd'hui, un responsable agit sur tous les employés.
- Pas de bouton « Changer d'entreprise » en cours de session : il faut se déconnecter puis se reconnecter. *(Choix du concepteur.)*
- Pas de modification du matricule ni de l'email depuis cet écran.

**Anti-objectifs**
- Désactiver une personne dans une entreprise ne doit pas la bloquer dans une autre entreprise où elle est active.
- Un employé désactivé qui peut encore pointer, par quelque chemin que ce soit.
- Des heures ou des pointages passés effacés ou modifiés par une désactivation.
- Une affectation qui chevauche une autre, ou un employé sans site à une date où il devrait en avoir un, après une mutation.

## 3. Règles métier

| Sujet | Règle |
|---|---|
| Qui agit | Les rôles MANAGER, HR, PAYROLL et ADMIN, avec un contrôle sur la route **et** dans le handler. *(Choix du concepteur, aligné sur les fonctionnalités de pointage.)* |
| Plafond des rôles | **Décision de l'utilisateur.** On ne modifie pas son propre rôle. On n'attribue pas un rôle supérieur au sien. On ne modifie, ne désactive et ne réactive pas une fiche dont le rôle est supérieur au sien. Le classement est celui de `Role.at_least` : EMPLOYEE < MANAGER < HR < PAYROLL < ADMIN. Violation : 403. |
| Entreprise d'une fiche | **Décision de l'utilisateur.** Une entreprise est un **annuaire racine** (`parent_directory_id` nul). Ses sous-annuaires sont des services ou des agences. La fiche employé **enregistre l'identifiant de son entreprise** (`company_directory_id`, l'annuaire racine de l'annuaire choisi à la création). Pour les fiches existantes, on le déduit de leur première affectation. Une affectation doit viser un annuaire de cette entreprise : la racine ou un descendant. Une mutation entre deux services de la même entreprise est permise. |
| Fiches existantes et valeur par défaut | **Décision de l'utilisateur.** Une migration passe **toutes les fiches existantes en actives**, une seule fois, par un événement de réactivation. La création d'une fiche se fait **active par défaut**. |
| Modifier : nom | Prénom et nom sont stockés sur le **compte** (User) et sont donc communs à toutes les entreprises de la personne. |
| Modifier : téléphone et rôle | Ils sont stockés sur la **fiche employé** et sont propres à l'entreprise. |
| Rôle du compte (`User.role`) | Il ne sert plus à la connexion dès que la personne a au moins une fiche employé (voir Connexion). Il n'est pas synchronisé avec les rôles des fiches. *(Choix du concepteur.)* |
| Désactiver | Concerne **la fiche employé** (`Employee.is_active = false`), pas le compte. La fiche ne peut plus pointer par aucun chemin : pointage normal, assisté, ou « Faire pointer ». Les pointages et les heures passés restent intacts. Les affectations ne sont pas modifiées. |
| Réactiver | Remet `is_active = true`, ce qui rouvre le pointage. |
| Se désactiver soi-même | Refusé. Un responsable ne peut pas désactiver sa propre fiche, ce qui évite de s'enfermer dehors. *(Choix du concepteur.)* |
| Affecter | Le responsable choisit l'annuaire (l'entreprise de la fiche), le site et une date de début ≥ aujourd'hui. Une date de fin est facultative. |
| Mutation le jour même | Si l'affectation en cours **commence à la même date** que la nouvelle (correction du site juste après la création), elle est **remplacée** : un événement d'annulation est émis et elle n'est plus active. Les pointages déjà faits ne changent pas. *(Choix du concepteur.)* |
| Mutation | Si une affectation couvre déjà la date de début, elle est **terminée la veille**, dans la même transaction. Si une affectation **future** commence après la date de début, l'opération est refusée (409) : on ne réécrit pas un planning futur en silence. *(Choix du concepteur.)* |
| Affectation future | Elle est permise. Le pointage utilise l'affectation active **du jour** : c'est déjà le cas avec `find_active(employee_id, today)`. |
| Rattacher à une autre entreprise | L'onboarding accepte un email existant. Il réutilise alors le compte et crée une nouvelle fiche employé dans l'annuaire choisi, avec un nouveau matricule (unique, comme aujourd'hui), son rôle et son affectation initiale. Une personne ne peut avoir qu'une fiche **active** par entreprise (annuaire racine), y compris à la réactivation. *(Choix du concepteur.)* Le prénom et le nom saisis sont ignorés si le compte existe déjà, et l'interface l'indique. |

### Connexion
- **Par matricule** : la fiche employé est déterminée par le matricule. La connexion est refusée si cette fiche est inactive.
- **Par email** (mot de passe ou code) : on calcule les fiches **actives** du compte.
  - **0 fiche active, mais au moins une fiche** : la connexion est refusée (« Aucun accès actif »).
  - **0 fiche et aucune fiche du tout** (compte sans employé, comme le compte ADMIN fondateur) : comportement actuel, avec le rôle du compte.
  - **1 fiche active** : la session est liée à cette fiche.
  - **Plusieurs fiches actives** : l'API renvoie une réponse « choix nécessaire » avec la liste des entreprises (`employeeId`, nom de l'annuaire, rôle) et un **jeton de sélection** court, valable 5 minutes. Le client renvoie ce jeton avec l'`employeeId` choisi pour obtenir la paire de jetons.
- **Jeton d'accès** : il porte `employee_id` (nullable) et le **rôle de la fiche**, ou celui du compte s'il n'y a pas de fiche. `PrincipalDTO` gagne `employee_id`.
- **Rafraîchissement** : la session (refresh token) mémorise l'`employee_id`. Si la fiche a été désactivée entre-temps, le rafraîchissement échoue et l'app revient à l'écran de connexion. *(Choix du concepteur.)*
- **Pointage pour soi** : il utilise `principal.employee_id` quand il est présent, au lieu de `find_by_user_id`.
- **Exclusions d'une décision ou d'un pointage manager sur soi-même** : elles comparent désormais toutes les fiches de la personne.

## 4. Conception technique (indicative, le builder ajuste)

### Backend : identity
- **Modifier**
  - Implémenter `PATCH /employees/{id}` avec le corps `{firstName?, lastName?, phone?, role?}`.
  - Côté domaine : `Employee.update(phone, role)` et `User.update_profile(first_name, last_name)`. Le handler existant `UpdateUserProfileHandler` peut servir pour le nom.
  - Les deux agrégats sont mis à jour dans une même transaction.
- **Désactiver / réactiver**
  - Routes `POST /employees/{id}/deactivate` et `POST /employees/{id}/activate`.
  - Événements dédiés, ou réutilisation de l'événement de mise à jour. La relecture des anciens événements doit rester compatible.
- **Affecter**
  - `POST /employee-assignments` gagne le contrôle de rôle et la mutation automatique : la fin de l'affectation en cours à la veille et la création de la nouvelle se font dans une seule commande et une seule unité de travail.
  - `POST /employee-assignments/{id}/end` gagne le contrôle de rôle.
- **Rattacher**
  - `POST /employees/onboard` : si l'email existe, le compte est réutilisé (plus d'erreur `EMAIL_ALREADY_REGISTERED`).
  - Une seule fiche active par annuaire racine, sinon 409.
- La lecture d'un employé (`EmployeeResponse`) gagne `firstName`, `lastName`, `directoryId`/`directoryName` et l'affectation en cours (site et dates), pour la fiche et la liste.

### Backend : auth
- `issue_access_token(user_id, role, employee_id)` et décodage correspondant ; `PrincipalDTO.employee_id`.
- Le login (mot de passe, code OTP) et le refresh suivent les règles de la section 3.
- Nouvelle route `POST /auth/select-employee` avec `{selectionToken, employeeId}`, qui renvoie la paire de jetons.
- Le refresh token stocke `employee_id`. Il faut une colonne nullable dans la table auth (base d'écriture) et une migration SQL idempotente.

### Backend : punch
- Le pointage normal, le pointage assisté et le pointage manager refusent une fiche inactive (404 ou 409 `EMPLOYEE_INACTIVE` : choix laissé au builder, avec un message français côté app).
- Le pointage normal lit `principal.employee_id`.

### Frontend : back-office (fiche employé)
- **Boutons** : « Modifier », « Désactiver » / « Réactiver » et « Affecter à un site ».
- **Modifier** : un formulaire avec prénom, nom, téléphone et rôle.
- **Désactiver** : une confirmation « Désactiver {nom} ? Il ne pourra plus pointer. ».
- **Affecter**
  - Le formulaire contient l'annuaire (pré-rempli), le site, la date de début (aujourd'hui par défaut, pas de date passée) et une date de fin facultative.
  - Si une affectation en cours existe, un avertissement l'indique : « L'affectation actuelle à {site} se terminera le {veille}. ».
- **Historique des affectations** : la liste des affectations, de la plus récente à la plus ancienne, avec un bouton « Terminer » sur l'affectation en cours ou future.
- **Création** : si l'email saisi existe déjà, un message l'indique : « Ce compte existe déjà : une nouvelle fiche sera créée dans cette entreprise. ».
- **Liste** : elle affiche le nom, l'entreprise et le site en cours.

### Frontend : connexion (mobile et back-office)
- Après une connexion qui renvoie « choix nécessaire », un écran « Dans quelle entreprise voulez-vous vous connecter ? » liste les entreprises et le rôle de chacune.
- La session conserve l'entreprise choisie, et son nom s'affiche en haut de l'écran.

### Frontend : app mobile
- L'écran « Employés » des responsables donne accès à la fiche avec les mêmes actions. Les widgets responsives sont réutilisés.

## 5. Tests attendus (principaux)
- **Domaine et relecture** : les nouveaux événements Employee rejouent, et les anciens aussi.
- **Mutation**
  - L'affectation en cours est terminée la veille.
  - Une affectation future en conflit donne 409.
  - Une date passée donne 422.
  - Le pointage d'aujourd'hui utilise toujours l'ancien site tant que la mutation n'a pas commencé.
- **Désactivation**
  - Le pointage normal, le pointage assisté et le pointage manager sont refusés.
  - Le compte reste utilisable dans l'autre entreprise.
  - On ne peut pas se désactiver soi-même.
- **Connexion**
  - 1 fiche donne un jeton direct.
  - 2 fiches donnent « choix nécessaire », puis un jeton portant le bon `employee_id` et le bon rôle.
  - Un jeton de sélection expiré ou falsifié donne 401.
  - Toutes les fiches désactivées donnent un refus.
  - Un compte sans fiche garde le comportement actuel.
  - Un refresh après désactivation échoue.
- **Rattachement** : un email existant donne une nouvelle fiche et le même compte. Une deuxième fiche active dans le même annuaire racine donne 409.
- **Rôles**
  - Chaque nouvelle route renvoie 403 pour EMPLOYEE.
  - Plafond : un MANAGER ne peut ni nommer quelqu'un HR ou ADMIN, ni modifier son propre rôle, ni désactiver un ADMIN.
- **Mutation le jour même** : l'affectation du jour est remplacée et les pointages sont intacts.
- **Migration** : les fiches existantes deviennent actives et reçoivent `company_directory_id`.
- **Frontend** : les formulaires, les confirmations, l'écran de choix d'entreprise et les messages d'erreur.

## 6. Laissé au builder
- Les noms exacts des routes, des commandes et des événements.
- Le format du jeton de sélection (JWT court signé, `typ` dédié).
- Le code d'erreur pour une fiche inactive.
- La forme de l'historique des affectations à l'écran.
- La forme de la migration ponctuelle (script dans `src/scripts/` ou commande) qui active les fiches existantes et renseigne `company_directory_id`.
