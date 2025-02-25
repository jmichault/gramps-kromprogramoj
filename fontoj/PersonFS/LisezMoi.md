

Ceci est une extension pour interfacer _gramps_ avec _familysearch.com_.
elle se compose de :
* un [_gramplet_](https://www.gramps-project.org/wiki/index.php/Gramplets) permettant de comparer votre individu avec celui de _FamilySearch_. Depuis ce gramplet, vous pouvez aussi faire des recherches sur familysearch, consulter les doublons potentiels trouvés par FamilySearch, copier les évènements vers ou depuis FamilySearch, importer les ancêtre et descendants.
* un module d'import accessible par le menu «Outils» --> «Modification de l'arbre familial» --> «Import de données FamilySearch»
* un module de comparaison accessible par le menu «Outils» --> «Modification de l'arbre familial» --> «FamilySearch : comparer»

Pour pouvoir utiliser l'extension il vous faut un compte _familysearch_, celui-ci sera demandé au lancement du gramplet, ainsi que le mot de passe associé.

# installation
## prérequis
Cette extension est prévue pour gramps version 6.0.
Elle a besoin de gir1.2-webkit2-4.0 .
Le gramplet utilise les modules python «requests» et «gedcomx\_v1» (>=1.0.12).  
Vous pouvez installer «requests» et «gedcomx\_v1» manuellement, ou laisser le gramplet les installer automatiquement (nécessite pip).
En raison des changements intervenus sur le site FamilySearch, ce plugin ne fonctionne plus sous Windows.

## ajout du projet dans le gestionnaire de greffons
* ouvrez le gestionnaire de greffons (icône «puzzle», ou menu Édition-->Gestionnaire de greffons)
* allez à l'onglet «Projets»
  * cliquez sur «+»
    * Nom du Projet : jmichault (ou ce que vous voulez)
    * URL : https://raw.githubusercontent.com/jmichault/gramps-kromprogramoj/gramps52
    * cliquez sur «Valider»
* allez à l'onglet «Greffons»
  * cherchez PersonFS
  * cliquez sur «Installer»

# le gramplet
## activation
En étant positionné sur le panneau des Individus, cliquez sur le menu déroulant à droite des onglets (petit bouton «v») et choisissez «Ajouter un Gramplet», puis «FS».  
Une fois ceci fait, un nouvel onglet «FS» est ajouté.

## utilisation

Le gramplet permet de comparer la fiche de votre personne gramps avec celle de familysearch pour les informations suivantes :  
* nom/prénom principal
* date et lieu de naissance
* date et lieu de baptême
* date et lieu de décès
* date et lieu de d'inhumation
* les parents (nom/prénom principal, années de naissance et de décès)
* les conjoints
* les enfants
* les autres évènements

La première colonne permet de visualiser rapidement quelles données ne sont pas en phase :
* vert = en phase (attention : pour les personnes seuls les identifiants familysearch sont vérifiés, pour les dates/lieux, seules les dates sont vérifiées)
* rouge : renseignement essentiel discordant. (renseignements essentiels = nom/prénom principal, sexe, dates de naissance et de décès)
* orange : présent des deux côtés, mais pas en phase.
* jaune : présent que dans gramps.
* jaune sombre : présent que dans FamilySearch.

Note : le lien avec _familysearch_ se fait grâce à un attribut de clé _«\_FSFTID»_ et ayant pour valeur le N° d'identification _familysearch_.  

Note : pour limiter le temps de chargement, au lancement les données détaillées des conjoints et enfants ne sont pas chargées. Vous pouvez les charger en cliquant sur le bouton «Rafraichir».

Les dates sont affichés chaque fois que c'est possible en utilisant le format [_«formal»_](https://github.com/FamilySearch/gedcomx/blob/master/specifications/date-format-specification.md) de _familysearch_.

Depuis le gramplet, vous pouvez aussi :
* Accéder à la fiche FamilySearch complète en cliquant sur le N° d'identification (à droite de l'écran), ce qui lance votre navigateur internet.
* Lancer une recherche sur FamilySearch, qui vous permet aussi d'associer votre fiche à une fiche familysearch existante, ou de créer la personne dans FamilySearch si vous ne trouvez pas de correspondance.
  * Attention : la personne est créée avec le minimum de renseignements : nom, prénom. À vous de transférer les autres renseignements, et de la lier à ses enfants, conjoints, parents.
* Consulter les doublons potentiels proposés par FamilySearch, et de là vous pouvez accéder à la fiche FamilySearch complète du doublon potentiel, ou accéder à l'écran de fusion FamilySearch.
* lancer le module d'import pour importer les données FamilySearch de votre individu, et éventuellement les ancêtres et descendants.
* copier des noms ou des évènements vers ou depuis FamilySearch en cochant la dernière colonne, puis en utilisant le menu contextuel (clic droit).
  * attention : les lieux qui ne sont pas normalisés dans FamilySearch ne sont pas copiés.
  * attention : Pour les évènements familiaux, FamilySearch n'accepte que les types suivants :  
        «Mariage», «Annulation»,«Divorce»,«Mariage de droit coutumier»,«A vécu maritalement», «Aucun enfant».  
      pour pouvoir transférer les «Contrat de mariage»,«Fiançailles»,«Publications de mariage», on les transforme en «Mariage» avec une explication «http://gedcomx.org/xxxxx»
* changer d'individu en double-cliquant sur la ligne correspondante.
* éditer un évènement de la personne en double-cliquant sur la ligne correspondante.
* utiliser le mode «Notes» pour comparer/transférer les notes individuelles et familiales
* utiliser le mode «Sources» pour comparer les sources (*expérimental, à n'utiliser qu'avec prudence*).
  * la gestion des sources est très différente dans gramps et FamilySearch, aussi le transfert ne gére que les données suivantes :
    * dans le sens citation saisie dans gramps vers FamilySearch :
      * le titre est constitué de la première ligne de la note de type citation.  
          (donc vous devez saisir votre citation en en tenant compte : vous devez avoir une note de type «Citation», et la première ligne doit correspondre au titre que vous voulez voir apparaitre)
      * la référence est constituée de :
        1. une ligne pour le dépôt : `Dépôt : titre_du_dépôt`
        2. une ligne pour la source : `Source : titre_de_la_source`
        3. une ligne pour la page : `Volume/Page : page_saisie_pour_la_citation`
        4. une ligne pour le niveau de confiance , par exemple : `Niveau de confiance : Très haut`
      * la Note est constituée de la concaténation de toutes les notes de la citation (sans reprendre le titre).
      * l'url est récupérée dans l'attribut 'Adresse Internet' de la citation.
    * dans le sens FamilySearch vers gramps.
      * si la source est de type FSREADONLY (i.e. une donnée fournie par FamilySearch) :
        * on crée une source correspondant à la collection du document FamilySearch (qui se trouve sur la première ligne de la référence).
        * on relie la source au dépôt «FamilySearch»
      * …

# le module d'import
Vous pouvez le lancer soit depuis le menu, soit depuis le gramplet.  
Vous avez juste à renseigner :
* l'identifiant FamilySearch de départ
* le nombre de générations d'ascendants à charger.
* le nombre de générations descendantes.
* cochez «Ne pas réimporter les personnes existantes» si vous voulez protéger vos individus existants.
* cochez «Ajouter les conjoints» si vous voulez charger aussi les conjoints de toutes les personnes.
  (note : si vous chargez des générations descendantes, les conjoints seront forcément chargés)
* cochez «Ajouter les sources» si vous voulez charger aussi les sources attachées.
* cochez «Ajouter les notes» si vous voulez charger aussi les notes attachées.

Puis cliquez sur le bouton «Importer»

# le module de comparaison
* cet outil va parcourir tous les individus et positionner les étiquettes suivantes :
  * FS\_Identa : tous les éléments comparés sont synchrones
  * FS\_Esenco : il y a une information essentielle à synchroniser (nom/prénom principal, dates de naissance et décès).
  * FS\_Nomo : il y a un nom (autre que le principal) à synchroniser.
  * FS\_Gepatro : il y a un parent à synchroniser.
  * FS\_Familio : il y a un conjoint ou un enfant à synchroniser.
  * FS\_Fakto : il y a un évènement à synchoniser (autre que naissance ou décès).
  * FS\_Dup : doublon potentiel détecté par FamilySearch.
  * FS\_Dok : documents à relier détectés par FamilySearch.
  * FS\_Gramps : changé dans gramps depuis la dernière fois que l'étiquette FS\_Konf a été positionné, ou que tout était conforme (étiquette FS\_Identa et aucun autre)
  * FS\_FS : changé dans FamilySearch depuis la dernière fois que l'étiquette FS\_Konf a été positionné, ou que tout était conforme (étiquette FS\_Identa et aucun autre)
* de plus l'étiquette FS\_Konf peut être positionnée depuis le gramplet : synchro pas parfaite mais marquée conforme.
* l'outil peut être interrompu en cours de traitement.

# méthode de travail suggérée.

## Créez des filtres
1. créez un filtre sélectionnant les individus qui vous intéressent, par exemple : «ascendants sur x générations»

## démarrage
1. activez le gramplet sur la vue Individus
2. allez sur votre individu souche, et liez-le :
  * avec le bouton chercher, essayez de le trouver dans familysearch
  * si vous le trouvez : utilisez le bouton Lier.
  * si vous ne le trouvez pas : utilisez le bouton Ajouter.
3. faites de même avec ses parents, puis les parents de ses parents …


## très régulièreent
1. consultez les lieux. Le transfert de données FamilySearch a très probablement créé des doublons : fusionnez les avec vos lieux pré-existants, ou mettez-les à vos propres normes.

## régulièrement
1. exécutez le module de comparaison
2. filtrez les «ascendants» avec l'étiquette FS_Gepatro
  * synchronisez les parents
3. filtrez les «ascendants» avec l'étiquette FS_Familio
  * synchronisez les enfants
4. procédez de même avec les étiquettes FS_Esenco, FS_Fakto, FS_Nomo
5. filtrez les «ascendants» avec l'étiquette FS_Dok
  * cliquez sur le lien menant à FamilySearch et vérifiez les documents proposés.
6. filtrez les «ascendants» avec l'étiquette FS_Dup
  * cliquez sur le bouton «Voir les doublons FS» et vérifiez s'il faut les fusionner.
