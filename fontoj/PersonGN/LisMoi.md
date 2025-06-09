# Résumé de l'extension Gramplet « PersonGN » pour Gramps
PersonGN est une extension Gramplet pour la catégorie Personne du logiciel de généalogie Gramps. Elle permet aux utilisateurs d'interagir avec la plateforme collaborative Geneanet (un site similaire à Ancestry.com proposant depuis 1996 le partage d'arbres généalogiques freemium) directement depuis Gramps.

Elle permet l'importation et la mise à jour sélectives d'une personne sélectionnée et de ses proches parents sur Geneanet.

## Pour Gramps 6.0 :
Ajoutez le chemin d'accès au projet expérimental de Jean Michault sur GitHub pour permettre l'installation via le [Gestionnaire des extensions](https://gramps-project.org/wiki/index.php/Gramps_Glossary/fr#addon "Lien vers le wiki Gramps").  
```https://raw.githubusercontent.com/jmichault/gramps-kromprogramoj/gramps60```
Recherchez ensuite PersonGN ou Geneanet dans l'onglet Modules complémentaires.

## Pour Gramps 5.2 :
Essayez d'utiliser le [Gestionnaire de modules complémentaires](https://gramps-project.org/wiki/index.php/Gramps_Glossary/fr#addon "Lien vers le wiki Gramps") comme avec Gramps 6.0. Si cela ne fonctionne pas, téléchargez l'archive PersonGN.addon.tgz et extrayez le dossier PersonGN dans le dossier gramps52/plugins.
<https://github.com/jmichault/gramps-kromprogramoj/tree/gramps60/download>

# Fonctionnalités principales
* Intégration à Geneanet : PersonGN permet aux utilisateurs de rechercher, de comparer et d'importer des données généalogiques sur des individus depuis Geneanet dans leur base de données d'arbres généalogiques Gramps.
* Interface utilisateur graphique : L'extension crée une interface graphique GTK, chargeant sa mise en page depuis un fichier Glade. Elle offre des commandes pour la recherche, la sélection et l'importation de données.
* Gestion des dépendances : Au démarrage, l'extension vérifie les dépendances Python requises (lxml, protobuf) et fournit des instructions à l'utilisateur si elles sont manquantes.
* Comparaison de données : L'extension récupère les données de Geneanet et les compare à la personne Gramps sélectionnée, affichant les différences dans un tableau détaillé et interactif. Les utilisateurs peuvent consulter les faits, les relations et autres attributs côte à côte.
* Importation sélective de données : Les utilisateurs peuvent sélectionner les faits, les relations (parents, conjoints, enfants) ou les événements Geneanet à importer ou à mettre à jour dans Gramps. Une sélection dans les Préférences permet d'exclure les Notes.
* Gestion des relations familiales : L'extension prend en charge l'importation et la mise à jour de relations familiales, telles que l'ajout ou la mise à jour des parents, des conjoints, des enfants et des événements associés (comme le mariage).
* Importation d'événements et de notes : L'extension permet d'importer ou de mettre à jour des événements (par exemple, naissance, décès, mariage) et des notes des fiches Geneanet dans Gramps, garantissant ainsi la cohérence des données et évitant les doublons.
* Langue : L'interface de l'extension en espéranto a été traduite en français, anglais, hébreu, néerlandais et portugais brésilien.
* Suivi de la progression : Lors de la récupération des données, l'extension affiche le nombre d'individus potentiellement compatibles en cours d'analyse, fournit un suivi de la progression et permet l'annulation.
# Détails techniques
* Utilise l'API Gramps : L'extension exploite largement les API internes de Gramps pour les transactions de base de données, la gestion des personnes et des familles, et la gestion des événements.
* Structure modulaire : Le code est modulaire et s'appuie sur des modules d'aide (par exemple, komparoGN, ImportoGN, utilaGN) pour la comparaison, la logique d'importation et les fonctions utilitaires.
* Gestion des erreurs : L'extension vérifie les fenêtres actives et gère les exceptions pour éviter les conflits lors de l'édition.
* Open Source : Sous licence GPL 3.0.

# Flux de travail typique
* Ajoutez le gramplet « Geneanet » à la barre inférieure ou à une vue de catégorie Personne.
* Sélectionnez une personne.
* Cliquez sur le bouton « Rechercher ».
* PersonGN récupère les données potentiellement correspondantes de Geneanet dans une liste.
* Les correspondances potentielles sont affichées sous forme de tableau résumant les faits et les relations.
* Sélectionnez la personne à importer pour consultation.
* Cliquez sur le lien « Afficher sur Geneanet » pour consulter les données dans un navigateur ;
* ou cliquez sur le bouton « Comparer » pour consulter les données dans le gramplet.
* Chaque ligne est codée par couleur pour indiquer l'état de synchronisation : différences, nouvelles données, conflits ou correspondances.
* Cochez les cases des lignes de données à importer.
* Cliquez sur le bouton « Importer la sélection », ou sur « Copier un choix de Geneanet vers Gramps » dans le menu contextuel accessible par clic droit.
* Les données sont copiées dans Gramps, mettant à jour l'arbre généalogique si nécessaire.

# Objectif
PersonGN simplifie le processus de synchronisation et d'enrichissement des données généalogiques dans Gramps depuis Geneanet, réduisant ainsi la saisie manuelle des données et garantissant leur exactitude et leur exhaustivité.

