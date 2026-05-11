"""Fill the EVAL_V3 evaluation grid Excel."""
from openpyxl import load_workbook

src = r'C:\Users\Mister Squishi\Downloads\Grille_EVAL_V3 (1).xlsx'
dst = r'C:\Users\Mister Squishi\Downloads\Grille_EVAL_V3_BEELEN_v2.xlsx'

wb = load_workbook(src)
sh = wb.active

# --- Infos etudiant ---
sh['B5'] = 'Beelen Mathieu'
sh['B6'] = 'q250036'

# --- Section 1 : Pre-requis ---
prereq = {
    12: "Projet depose avant 23h55 le 30/04/2026 sur Panoramix.",
    13: "Grille d'auto-evaluation deposee sur Learn dans les delais.",
    14: "Tous les fichiers .html ont ete convertis en .php. Aucun .html dans EVAL_V3/.",
    15: "festival.sql present a la racine du projet, script MySQL fonctionnel.",
    16: "Architecture MVC : pages a la racine, Model/ pour la BD, View/ pour les partials (header, footer, cards), controleur/ pour les helpers, vendor/ pour Composer/PHPMailer.",
    17: "3 artistes (Veronica, Louis, Anna), 1 organisateur (Marta), 5 prestations par artiste (15 au total), 3 scenes, 6 prestations programmees.",
    18: "Toutes les pages publiques (accueil, artistes, prestations, contacts) lisent dynamiquement depuis la BD via PDO. Aucun contenu statique en dur.",
    19: "Grille completee avec serieux, justifications detaillees pour chaque critere.",
}
for row, just in prereq.items():
    sh[f'C{row}'] = just
    # NE PAS toucher D : les checkboxes natives Excel se cassent. L'utilisateur clique.

# --- Section 2 : Conformite (UCs) ---
ucs = {
    25: "Grille generee par index.php : scenes en colonnes via Scene::listerTous(), heures en lignes via Programmation::lireHeuresUtilisees() qui ne renvoie que les heures effectivement utilisees (pas de ligne vide).",
    26: "Chaque cellule affiche titre + nom_artiste, joints via INNER JOIN sur prestation et artiste.",
    27: "Lien <a href='prestation.php?id=...'> dans chaque cellule.",
    28: "Si planning vide, message 'Aucune prestation n'est encore programmee' affiche.",
    29: "artistes.php affiche la galerie via View/card-artiste.php (photo + nom_artiste + lien profil).",
    30: "Pour chaque artiste programme, listerParArtiste filtre sur 'programmees' affiche heure_debut, scene_nom et titre.",
    31: "Lien dans card-artiste.php vers artiste.php?id=... cliquable.",
    32: "Checkbox 'programmes' (parametre GET) passe le filtre booleen a Artiste::listerTous(true).",
    33: "artiste.php affiche nom, prenom, nom_artiste, photo et description via Artiste::trouverParId().",
    34: "Liste des prestations de l'artiste rendue en vignettes via View/card-prestation.php.",
    35: "card-prestation.php affiche heure_debut + scene_nom si la prestation est programmee.",
    36: "Lien <a href='prestation.php?id=...'> dans chaque vignette.",
    37: "prestations.php utilise card-prestation.php (image, titre, nom_artiste).",
    38: "Affichage de heure_debut + scene_nom si la prestation est programmee.",
    39: "Lien <a> vers prestation.php?id=... dans chaque vignette.",
    40: "Formulaire GET avec champs motCle, idCategorie, idArtiste, programmees, traites par Prestation::rechercher() avec WHERE dynamique et parametres prepares.",
    41: "Si tableau de resultats vide, message 'Aucune prestation ne correspond a votre recherche' affiche.",
    42: "prestation.php affiche titre, description, image et categorie via Prestation::trouverParId().",
    43: "Si scene_nom non null : 'Programmee : HH-HH sur Scene X' affiche clairement.",
    44: "contacts.php avec champs nom, email, sujet (select), message.",
    45: "Validation serveur via valRequis() + valEmail() + valMaxLong() avant envoi via PHPMailer (Composer).",
    46: "profil.php pre-rempli avec donnees BD via Artiste::trouverParId() / Utilisateur::trouverParId(). Champs nom, prenom, nom_artiste, description, email, mot de passe.",
    47: "validation.php centralise les regles. Messages d'erreur affiches par champ avec class 'erreur-texte'.",
    48: "Utilisateur::emailExiste(email, exceptId) avec exception de l'utilisateur courant pour permettre la modification.",
    49: "Utilisateur::modifier() et Artiste::modifier() avec PDO prepared statements (UPDATE...WHERE id = :id).",
    50: "Helper old() repopule les valeurs POST dans les champs en cas d'erreur de validation.",
    51: "mes-prestations.php?action=ajouter avec titre, description, categorie (select). Image non requise (cf enonce).",
    52: "valRequis(), valMaxLong(), valDansListe() avec messages specifiques par champ.",
    53: "Prestation::creer() insere avec artiste_id provenant de la session de l'artiste connecte.",
    54: "Helper old() repopule en cas d'erreur.",
    55: "action=modifier&id=X charge la prestation existante et la pre-affiche dans le formulaire.",
    56: "Memes regles de validation serveur que pour l'ajout.",
    57: "Prestation::modifier() avec UPDATE prepared statement.",
    58: "Helper old() repopule en cas d'erreur en mode edition.",
    59: "action=supprimer affiche une page de confirmation. La suppression effective necessite un POST avec confirme=oui.",
    60: "Prestation::estProgrammee() verifie AVANT le DELETE. Si programmee, message clair 'demandez a l'organisateur de la deprogrammer'.",
    61: "DELETE FROM prestation WHERE id = :id execute apres confirmation utilisateur.",
    62: "tableau-bord-artiste.php affiche nom_artiste et photo (big-avatar-img).",
    63: "Liste des prestations programmees (heure_debut + scene_nom + titre) via Prestation::rechercher avec filtre programmees.",
    64: "Boutons 'Editer mon profil' (vers profil.php) et 'Gerer mon catalogue' (vers mes-prestations.php).",
    65: "deprogrammer.php reutilise la meme structure scenes x heures que index.php.",
    66: "Lien <a class='lien-danger'> 'Deprogrammer' dans chaque cellule programmee.",
    67: "action=confirmer affiche page de confirmation avant la deprogrammation effective.",
    68: "Programmation::supprimer() execute DELETE FROM programmation WHERE id = :id.",
    69: "gerer-artistes.php affiche la liste de tous les artistes via Artiste::listerTous().",
    70: "Lien 'Gerer' vers gerer-artiste.php?id=X pour chaque artiste.",
    71: "action=profil dans gerer-artiste.php avec validation et update via Utilisateur::modifier() + Artiste::modifier().",
    72: "action=prest-modifier et action=prest-supprimer disponibles pour l'organisateur sur les prestations de chaque artiste.",
}
for row, just in ucs.items():
    sh[f'C{row}'] = just
    # NE PAS toucher D : checkboxes Excel preservees pour clic manuel

# --- Section 3 : AA3 / AA4 / AA6 ---
aa3 = {
    79: "vendor/validation.php centralise les regles (valRequis, valEmail, valMaxLong, valMinLong, valDansListe, valEgales) avec messages d'erreur specifiques par champ. Toute validation est cote serveur, l'attribut HTML5 'novalidate' desactive la validation navigateur.",
    80: "Helper old() dans helpers.php utilise $_POST pour repopuler les valeurs apres erreur. Applique sur TOUS les formulaires (contacts, login, inscription, profil, prestations).",
    81: "classeErreur() retourne la classe CSS 'field-error' (rouge + fond clair) si le champ a une erreur. Message d'erreur affiche dans <span class='erreur-texte'> directement sous le champ.",
}
aa4 = {
    84: "7 tables conformes au MCD : utilisateur (parent), artiste / organisateur (specialisations 1-1), categorie, scene, prestation (avec FK artiste_id et categorie_id), programmation (table d'association avec heure_debut comme attribut).",
    85: "Tous les modeles utilisent PDO::prepare() avec parametres nommes (:nom, :id, :artiste_id, etc.). Aucune concatenation de variables utilisateur dans les requetes : protection totale contre les injections SQL.",
    86: "CRUD complet et structure : Prestation::creer/modifier/supprimer/rechercher, Utilisateur::inscrireArtiste/modifier/trouverParEmail, Programmation::supprimer/listerTous/lirePlanning, separes proprement en methodes statiques par modele.",
    87: "FOREIGN KEY avec ON DELETE CASCADE pour la coherence (artiste/utilisateur, prestation/artiste, programmation/prestation). Jointures INNER JOIN et LEFT JOIN dans les SELECTs (artiste-utilisateur, prestation-categorie, programmation-scene, etc.).",
    88: "PDO configure en ERRMODE_EXCEPTION : toute erreur SQL leve une PDOException. Transaction beginTransaction()/commit()/rollBack() dans inscrireArtiste pour garantir la coherence (insertion utilisateur + artiste atomique). Verifications metier comme estProgrammee() avant DELETE.",
}
aa6 = {
    91: "Helpers separes par responsabilite : helpers.php (h, old, redirect, postParam, getInt, classeErreur, formatHeure), auth.php (sessions, connecter/deconnecter, simulerOrganisateur), validation.php (regles). Vues partielles reutilisables (header, footer, card-artiste, card-prestation) evitent la duplication HTML.",
    92: "Pattern MVC clair : Model/ contient la logique BD (classes namespaced App\\Model), View/ les partials, controleur/ les utilitaires, pages a la racine. Singleton Database evite les connexions multiples. Autoload PSR-4 via Composer.",
    93: "Helper h() = htmlspecialchars(value, ENT_QUOTES, 'UTF-8') applique SYSTEMATIQUEMENT sur toute sortie HTML provenant de la BD ou de l'utilisateur. Verifiable dans tous les fichiers (cards, pages, formulaires repopules).",
    94: "Strict typing avec type hints (string, int, ?array, void). Try/catch sur les operations critiques (Database connection, PHPMailer). Aucun warning ou notice non gere. Tests sur null avec ?? et type-safe casts.",
    95: "Noms explicites en francais (postParam, valRequis, classeErreur, simulerOrganisateur, estProgrammee, etc.). DRY respecte via partials et helpers (zero duplication HTML/PHP). Code commente en francais. Conventions coherentes (PascalCase classes, camelCase methods).",
}

for row, just in aa3.items():
    sh[f'C{row}'] = just
    sh[f'D{row}'] = sh[f'E{row}'].value  # 7/7 - features concretes implementees

# AA4 : 17/18 (humilite sur la gestion d'erreurs BD)
for row, just in aa4.items():
    sh[f'C{row}'] = just
    sh[f'D{row}'] = sh[f'E{row}'].value
# Reduction honnete : la gestion d'erreurs BD est limitee (try/catch surtout sur la connexion)
sh['D88'] = 2  # au lieu de 3
sh['C88'] = ("PDO en ERRMODE_EXCEPTION : les exceptions remontent. Transaction "
             "beginTransaction()/rollBack() dans inscrireArtiste pour la coherence. "
             "Verifications metier (estProgrammee avant DELETE). "
             "Le try/catch global est centralise dans Database, mais chaque query individuelle "
             "n'est pas wrappee dans son propre try/catch -- les exceptions remontent au niveau page.")

# AA6 : 17/20 (humilite sur 3 criteres subjectifs)
for row, just in aa6.items():
    sh[f'C{row}'] = just
    sh[f'D{row}'] = sh[f'E{row}'].value

# Architecture : bonne mais simple (pas de routing, pas de framework)
sh['D92'] = 3  # au lieu de 4
sh['C92'] = ("Pattern MVC clair : Model/ contient la logique BD (classes namespaced App\\Model), "
             "View/ les partials, controleur/ les utilitaires, pages a la racine. "
             "Singleton Database. Autoload PSR-4 via Composer. "
             "Architecture solide mais simple : pas de routing, pas de container "
             "d'injection de dependances, ce qui resterait a faire pour un projet plus ambitieux.")

# Gestion erreurs PHP : strict typing oui, mais pas de try/catch partout
sh['D94'] = 3  # au lieu de 4
sh['C94'] = ("Strict typing avec type hints (string, int, ?array, void). "
             "Try/catch sur les operations critiques (Database connection, PHPMailer). "
             "Operateur ?? pour null safety. "
             "Toutefois, certaines requetes ne sont pas explicitement wrappees dans des try/catch "
             "individuels : les exceptions remontent globalement.")

# Code maintenable : bien mais quelques fichiers long avec if par action
sh['D95'] = 3  # au lieu de 4
sh['C95'] = ("Noms explicites en francais (postParam, valRequis, classeErreur, simulerOrganisateur, "
             "estProgrammee, etc.). DRY respecte via partials et helpers. Code commente. "
             "Conventions coherentes (PascalCase classes, camelCase methods). "
             "A ameliorer : mes-prestations.php et gerer-artiste.php contiennent plusieurs actions "
             "dans un meme fichier (if action == 'X') -- un controleur dedie par action serait plus propre.")

wb.save(dst)
print(f'Saved: {dst}')
