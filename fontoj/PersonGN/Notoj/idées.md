

# objet
  importer des données de geneanet dans gramps. Vu que beaucoup d'arbres geneanet ont une fiabilité douteuse, on ne fera pas d'import automatique.
  L'import se fera depuis la comparaison de l'individu gramps avec l'individu geneanet.
  Dans le cas de l'ajout d'un individu (parent ou enfant), on se limitera à :
      nom, prénom, dates et lieux de naissance,décès,mariage.

# mémorisation du lien entre individu gramps et geneanet
 ajouter un attribut ,un lien internet, ou une citation ?
 * lien internet : semble le plus évident, permet de suivre le lien
 * attribut : on peut y ajouter une note ou une citation
 * citation : permet de savoir d'où viennent les informations. On peut mettre un niveau de confiance.
 
# gestion des arbres geneanet
 On mémorisera les arbres geneanet utilisés en tant que source (dépôt = geneanet).
 * mettre une étiquette GN\_exclure à ceux qu'on ne veut pas voir dans les résultats ?

# interface
 Une liste déroulante propose les liens geneanet déjà présents sur l'individu.
 On doit pouvoir faire une recherche sur geneanet.
   Une fois la recherche faite, les résultats cochés sont ajoutés temporairement à la liste déroulante.
 On peut aussi saisir (ou copier-coller) une URL.
 Quand on choisit un élément dans la liste déroulante, la comparaison est lancée.
 

