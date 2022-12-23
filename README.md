# Support du compteur Linky dans Home Assistant

Cette intégration pour Home Assistant ajoute le support des Linky au travers de n'importe quelle connection série en provenance du module TIC (Télé Information Client) du compteur Linky.

Par exemple:
* [Module série USB développé par LiXee](https://lixee.fr/produits/30-tic-din-3770014375070.html) (celui que j'utilise)
* [Module TELEINFO de CGE electronics](https://www.gce-electronics.com/fr/carte-electronique-oem-relais-USB/655-module-teleinfo-usb.html) (validé par un [utilisateur](https://github.com/hekmon/lixeeticdin/issues/1#issuecomment-1315264235))
* et certainement bien d'autres ! (n'hésitez pas à m'ouvrir une issue pour rajouter le votre si vous avez validé que le votre fonctionne avec cette intégration afin d'aidez de potentiels futurs utilisateurs qui n'en auraient pas encore choisi un)

[Exemple sous Home Assistant](https://github.com/hekmon/lixeeticdin/raw/v2.0.0-beta1/res/SCR-20221223-ink.png).

Théoriquement cette intégration est compatible avec les compteurs pré Linky qui possède un module TIC en choisissant le mode historique mais n'en ayant aucun dans mon entourage, je n'ai pas pu le vérifier.

## Informations remontées

Cette intégration va lire de manière continue les informations envoyées sur le TIC et stocker en mémoire la dernière valeur lue pour chacun des compteurs. Ensuite, Home Assistant viendra régulièrement et de lui même "récolter" les valeurs des différents sondes que l'intégration lui a déclarée. La fréquence est actuellement de 30 secondes mais ce n'est donc pas quelque chose qui est contrôlée par l'intégration mais bien par Home Assistant: il s'agit d'un compromis entre obtenir la valeure rapidement sans devoir lire une trame complète sur la connection série lors d'une demande de mise à jour et laisser Home Assistant décider de la fréquence de mise à jour des sondes. C'est largement suffisement pour la grande majoritée des sondes.

Cependant, certaines sondes peuvent avoir de la valeur dans leur "instantanéité" (relative). Pour cela, l'intégration possède une option "temps réel" qui peut être activée. Celle-ci ne passera pas toutes les sondes en temps réel mais seulement celles pour qui cela peut avoir du sens. Bien entendu, si vous activez cette option, attendez-vous à voir plus de ressources consommées (utilisation CPU mais aussi espace disque de la base de données sur le long terme). Cette option temps réel "poussera" directement la valeur qui vient d'être lue à Home Assistant et lui demandera de l'enregistrer au plus vite à la différence des autres sondes dont les valeurs sont récupérées par Home Assistant, à son rythme.

Suivant la configuration que vous choisirez pour votre installation vous trouverez dans ce fichier dans la liste des sondes avec les annotations suivantes:

* <sup>1</sup> sonde compatible avec le mode temps réel: si celui-ci est activé par l'utilisateur, les mises à jours seront bien plus fréquentes (dès qu'elles sont lues sur la connection série)
* <sup>2</sup> sonde dont le mode temps réel est forcé même si l'utilisateur n'a pas activé le mode temps réèl dans le cas où la valeur de la sonde est lue pendant une trame courte en raffale (ces trames sont émisent uniquement pour les compteurs triphasés en mode historique lors d'un dépassement sur l'une des phases)

### Mode historique

Le mode historique est le plus commun (existant pré Linky) : il est activé par défault à moins que vous soyez producteur d'énergie.

#### Compteurs mono-phasé

Les 23 champs des compteurs mono-phasé configurés en mode historique sont supportés:

* `ADCO` Adresse du compteur (avec parsing EURIDIS en attributs étendus et périphérique agrégateur sous Home Assistant)
* `OPTARIF` Option tarifaire choisie
* `ISOUSC` Intensité souscrite
* `BASE` Index option Base
* `HCHC` Index option Heures Creuses - Heures Creuses
* `HCHP` Index option Heures Creuses - Heures Pleines
* `EJPHN` Index option EJP - Heures Normales
* `EJPHPM` Index option EJP - Heures de Pointe Mobile
* `BBRHCJB` Index option Tempo - Heures Creuses Jours Bleus
* `BBRHPJB` Index option Tempo - Heures Pleines Jours Bleus
* `BBRHCJW` Index option Tempo - Heures Creuses Jours Blancs
* `BBRHPJW` Index option Tempo - Heures Pleines Jours Blancs
* `BBRHCJR` Index option Tempo - Heures Creuses Jours Rouges
* `BBRHPJR` Index option Tempo - Heures Pleines Jours Rouges
* `PEJP` Préavis Début EJP (30 min)
* `PTEC` Période Tarifaire en cours
* `DEMAIN` Couleur du lendemain
* `IINST` Intensité Instantanée <sup>1</sup>
* `ADPS` Avertissement de Dépassement De Puissance Souscrite <sup>1</sup>
* `IMAX` Intensité maximale appelée
* `PAPP` Puissance apparente <sup>1</sup>
* `HHPHC` Horaire Heures Pleines Heures Creuses
* `MOTDETAT` Mot d'état du compteur

#### Compteurs tri-phasés

⚠️ Actuellement en beta ⚠️

* `ADCO` Adresse du compteur (avec parsing EURIDIS en attributs étendus et périphérique agrégateur sous Home Assistant)
* `OPTARIF` Option tarifaire choisie
* `ISOUSC` Intensité souscrite
* `BASE` Index option Base
* `HCHC` Index option Heures Creuses - Heures Creuses
* `HCHP` Index option Heures Creuses - Heures Pleines
* `EJPHN` Index option EJP - Heures Normales
* `EJPHPM` Index option EJP - Heures de Pointe Mobile
* `BBRHCJB` Index option Tempo - Heures Creuses Jours Bleus
* `BBRHPJB` Index option Tempo - Heures Pleines Jours Bleus
* `BBRHCJW` Index option Tempo - Heures Creuses Jours Blancs
* `BBRHPJW` Index option Tempo - Heures Pleines Jours Blancs
* `BBRHCJR` Index option Tempo - Heures Creuses Jours Rouges
* `BBRHPJR` Index option Tempo - Heures Pleines Jours Rouges
* `PEJP` Préavis Début EJP (30 min)
* `PTEC` Période Tarifaire en cours
* `DEMAIN` Couleur du lendemain
* `IINST1` Intensité Instantanée (phase 1) <sup>1</sup> <sup>2</sup>
* `IINST2` Intensité Instantanée (phase 2) <sup>1</sup> <sup>2</sup>
* `IINST3` Intensité Instantanée (phase 3) <sup>1</sup> <sup>2</sup>
* `IMAX1` Intensité maximale (phase 1)
* `IMAX2` Intensité maximale (phase 2)
* `IMAX3` Intensité maximale (phase 3)
* `PMAX` Puissance maximale triphasée atteinte
* `PAPP` Puissance apparente <sup>1</sup>
* `HHPHC` Horaire Heures Pleines Heures Creuses
* `MOTDETAT` Mot d'état du compteur
* `ADIR1` Avertissement de Dépassement d'intensité de réglage (phase 1) <sup>2</sup>
* `ADIR2` Avertissement de Dépassement d'intensité de réglage (phase 2) <sup>2</sup>
* `ADIR3` Avertissement de Dépassement d'intensité de réglage (phase 3) <sup>2</sup>

### Mode standard

Le mode standard peut être considéré comme la "v2" du TIC développé par Enedis et a été introduit avec les Linky. Il transmets plus d'informations mais n'est activé qu'à la demande de l'utilisateur ou si celui-ci est producteur d'énergie. Le mode standard n'est pour le moment pas supporté même si j'envisage d'y passer moi même pour pouvoir le développer. Le coeur du module (lecture série du TIC) est théoriquement déjà compatible avec ce mode mais pas les entités Home Assistant (voir la partie Architecture).

## Installation

### Configuration du module

Une fois que votre module TIC est installé et connecté à votre compteur ainsi qu'un votre box domotique au travers de son cable USB, vous devriez voir apparaitre le périphérique `/dev/ttyUSB0` (ou `/dev/ttyUSB1` si vous aviez déjà une `/dev/ttyUSB0`).

Exemple de configuration pour le module de [LiXee](https://faire-ca-soi-meme.fr/domotique/2016/09/12/module-teleinformation-tic/):

* Mode historique
```bash
stty -F /dev/ttyUSB0 1200 sane evenp parenb cs7 -crtscts
```

* Mode standard (à vérifier)
```bash
stty -F /dev/ttyUSB0 9600 sane evenp parenb cs7 -crtscts
```

Vérifiez que celui-ci fonctionne correctement en lancant la commande (Ctrl+C pour quitter):

```bash
cat /dev/ttyUSB0
```

Vous devriez voir défiler les informations du TIC.

### Téléchargement

Dans la page des [releases](https://github.com/hekmon/lixeeticdin/releases) sélectionnez la version que vous souhaitez et copiez l'adresse de l'archive zip.

Ensuite rendez vous dans votre dossier `config` (celui ou le fichier `configuration.yaml` est présent) de Home Assistant et créez le dossier `custom_components` s'il n'existe pas déjà. Entrez à l'intérieur de celui-ci et téléchargez l'archive zip. Enfin décompressez la.

```bash
config_dir="/remplacez/par/le/votre"
mkdir -p "${config_dir}/custom_components"
cd !$
wget "<url_du_zip>" -O 'linky_tic.zip'
unzip 'linky_tic.zip'
rm -r 'linkytic' # seulement si vous aviez une précédente version du module
mv 'linkytic-<version_du_zip>' 'linkytic'
```

Remplacez toutes les valeurs entre `<...>`.

Vous devriez maintenant avoir le dossier `/votre/config/dir/custom_components/linkytic`.

Redémarrez votre Home Assistant !

#### Migration depuis la v1

L'intégration ayant changée de nom, n'oubliez pas d'enlever le bloc
```yaml
lixeeticdin:
  # [...]
```

de votre fichier `configuration.yaml` avant de redémarrer Home Assistant (ou redémarrez le une nouvelle fois).

### Activation et configuration dans Home Assistant

Une fois redémarré, allez dans: `Paramètres -> Appareils et services -> Ajouter une intégration`. Dans la fenêtre modale qui s'ouvre par la suite, cherchez `linky` et sélectionnez l'intégration s'appelant `Linky TIC` dans la liste (une petite icône d'un carton ouvert avec un texte de survol indiquant `Fourni par une extension personnalisée` devrait se trouver sur la droite).

Vous devriez passer sur le formulaire d'installation vous présentant les 3 champs suivants:
* `Chemin vers le périphérique série` Ici renseignez le path de votre périphérique USB testé précédement. Le champ est rempli par default avec la valeur `/dev/ttyUSB0`: Il ne s'agit pas d'une auto détection mais simplement la valeure la plus probable dans 99% des installations.
* `Mode TIC` Choississez entre `Standard` et `Historique`. Plus de détails sur ces 2 modes en début de ce document.
* `Triphasé` À cocher si votre compteur est un compteur... triphasé. À noter que cette option n'a d'effet que si vous êtes en mode historique (le mode standard gère le mono et le tri de manière indifférente).

Validez et patientez pendant le temps du test. Celui-ci va tenter d'ouvrir une connection série sur le périphérique désigné et d'y lire au moins une ligne correctement. En cas d'erreur, celle-ci vous sera retourné à l'écran de configuration. Sinon, fécilitations votre nouvelle intégration est prête et disponibles dans la liste des intégrations de la page où vous vous trouvez.

Pour ceux intéressé par le mode "temps réel", localisez l'intégration Linky TIC dans les tuiles de la page et cliquez sur `Configurer`.

#### Migration depuis la v1

Le passage au [config flow](https://developers.home-assistant.io/docs/config_entries_config_flow_handler) permettant notamment l'installation, la configuratione et la suppression depuis l'interface grahique directement plutôt qu'en passant par le fichier de [configuration YAML](https://developers.home-assistant.io/docs/configuration_yaml_index) (méthode dépréciée par Home Assistant) utilisé par la v1, a entrainé un changement en profondeur: chaque "unique ID" des sensors (une valeur interne que vous ne voyez pas) a dû changer pour s'accomoder à la partie dynamique des control flow.

Cela veut dire qu'en passant de la v1 à la v2 (vous avez bien pensez à retirer la déclaration de l'ancien nom de la v1 dans votre fichier de configuration ?) de nouvelles sondes vont être crées. Il est toute fois possible de faire un peu de ménage et de rattacher ces nouvelles sondes sur les anciens ID utilisateurs afin de conserver leur historique.

Possible mais fastidieux, à vous de voir:

* Une fois la v2 installée et configurée
* Depuis la tuile de l'intégration dans `Paramètres -> Appareils et services`, dirigez vous vers l'onglet `Entités` et faites une recherche avec `Linky`
* Vous devriez alors voir vos précédents sondes de l'intégration lixeeticdin et la nouvelle v2 Linky TIC".
* Par exemple pour la sonde de la puissance apparante:
  * `sensor.linky_puissance_apparente` liée à la v1
  * `sensor.linky_puissance_apparente_2` liée à la v2
* Cliquez sur celle de la v1 et supprimez là avec le bouton en bas à gauche
* Tout de suite après, cliquez sur celle de la v2 et renommez l'`ID Entité` de `sensor.linky_puissance_apparente_2` en `sensor.linky_puissance_apparente`
* Répétez l'oppération pour toutes les entitées (courage !)

## Développement
### Disclaimer

Je ne suis pas un habitué du python et encore moins du framework Home Assistant ! Ce module doit donc être largement améliorable. Néanmoins il permet le support simple et natif d'un maximum d'éléments transmis par le compteur Linky dans Home Assistant au travers d'une connection série du TIC.

### Architecture

![Schéma d'architecture du module](https://github.com/hekmon/lixeeticdin/raw/v2.0.0-beta1/res/linkytic_archi.excalidraw.png "Schéma d'architecture du module")

### Référence

Le document de référence du protocole TIC dévelopé par Enedis est [archivé dans ce repo](https://github.com/hekmon/lixeeticdin/raw/v1.0.1/Enedis-NOI-CPT_54E.pdf). Vous y trouverez toutes les informations nécessaire au dévelopement ainsi que des détails sur les informations remontées par ce plugin. Celui-ci et tout autre document de référence d'implémentation pouvant se trouver dans ce répertoire ne sont évidement pas couvert par la license MIT de ce repo et reste la propriété de leurs auteurs respectifs.
