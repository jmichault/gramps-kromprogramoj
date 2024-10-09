
Comment comparer les memories FS avec les media gramps ?

note : l'interface service est plus pratique pour obtenir les informations :
https://www.familysearch.org/service/memories/presentation/artifacts/197051022?includeAssociatedArtifacts=true&includeDatesPlaces=true&includeContactName=true&_=1726156704965&profile=skeleton


# propriétés des media gramps :
 * propriétés visibles :
   * Identifiant(gramps\_id) , titre(desc) , date , chemin(path) , étiquettes , type(mime)
   * attributs
   * citations
   * notes
 * propriétés cachées : checksum.
on doit avoir aussi quelque part le «thumbnail», car je me suis retrouvé avec un aperçu correspondant à l'ancienne version du fichier.

# propriétés des références de media gramps :
 * propriétés visibles :
   * media
   * référence : type, handle
   * privé?
   * rectangle
   * attributs
   * citations
   * notes
 * propriétés cachées : aucune.

# propriétés des memories FS :
 * classe Evidence
   * id
   * resourceId : la partie avant '-' donne l'id de la SourceDescription.
   * resource
   * links
 * classe SourceDescription
   * id
   * about : lien vers l'image
   * descriptions (set)
   * artifactMetadata (set)
   * links : liens vers :
     * artifact, comments, coverage, image, image-deep-zoom-lite, image-icon, image-thumbnail, memory, persons, …
   * mediaType (ex. : 'image/jpeg')
   * titles : titre(s)
   * coverage : set of Coverage :
     * spatial : PlaceReference = lieu
     * temporal : Date
   * …
 * classe artifactMetaData
   * filename, width, height, size

