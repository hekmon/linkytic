# Support du compteur Linky dans Home Assistant (module LiXee-TIC-DIN)

Cette intégration pour Home Assistant ajoute le support des Linky au travers du [module série USB développé par LiXee](https://lixee.fr/produits/30-tic-din-3770014375070.html).

## Informations remontées

### Mode historique

Le mode historique est le plus commun (existant pré Linky) : il est activé par défault a moins que vous soyez producteur d'énergie. Théoriquement ce module est compatible avec les compteurs pré-Linky qui possède un module TIC (voir la partie configuration du module) mais n'en ayant aucun dans mon entourage, je n'ai pas pu le vérifier.

#### Compteurs mono-phasé

Les 23 champs des compteurs mono-phasé configurés en mode historique sont supportés:

* `ADCO` Adresse du compteur (avec parsing EURIDIS en attributs étendus)
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
* `IINST` Intensité Instantanée
* `ADPS` Avertissement de Dépassement De Puissance Souscrite
* `IMAX` Intensité maximale appelée
* `PAPP` Puissance apparente
* `HHPHC` Horaire Heures Pleines Heures Creuses
* `MOTDETAT` Mot d'état du compteur

[Exemple sous Home Assistant](https://github.com/hekmon/lixeeticdin/raw/v1.0.1/res/SCR-20220706-inu.png).

#### Compteurs tri-phasés

Les compteurs tri-phasés et leurs entités ne sont pas supportés. En effet, ceux-ci comportent un mode de trame courtes émisent en "burst" dans certaines conditions que le coeur du module ne sait pas supporter. Et n'ayant pas accès à un tel compteur pour faire des tests je ne peux pas développer cette partie là.

### Mode standard

Le mode standard peut être considéré comme la "v2" du TIC développé par Enedis et a été introduit avec les Linky. Il transmets plus d'informations mais n'est activé qu'à la demande de l'utilisateur ou si celui-ci est producteur d'énergie. Le mode standard n'est pour le moment pas supporté même si j'envisage d'y passer moi même pour pouvoir le développer. Le coeur du module (lecture série du TIC) est théoriquement déjà compatible avec ce mode mais pas les entités Home Assistant (voir la partie Architecture).

## Installation

### Configuration du module

Une fois que votre module TIC-DIN est installé et connecté à votre compteur ainsi qu'un votre box domotique au travers de son cable USB, vous devriez voir apparaitre le périphérique `/dev/ttyUSB0` (ou `/dev/ttyUSB1` si vous aviez déjà une `/dev/ttyUSB0`).

Configurez le avec la commande suivante:

```bash
stty -F /dev/ttyUSB0 1200 sane evenp parenb cs7 -crtscts
```

Vérifiez que celui-ci fonctionne correctement en lancant la commande (Ctrl+c pour quitter):

```bash
cat /dev/ttyUSB0
```

Vous devriez voir défiler les informations du TIC.


Plus d'informations à la [source](https://faire-ca-soi-meme.fr/domotique/2016/09/12/module-teleinformation-tic/).

### Téléchargement

Dans la page des [releases](https://github.com/hekmon/lixeeticdin/releases) sélectionnez la version que vous souhaitez et copiez l'adresse de l'archive zip.

Ensuite rendez vous dans votre dossier `config` (celui ou le fichier `configuration.yaml` est présent) de Home Assistant et créez le dossier `custom_components` s'il n'existe pas déjà. Entrez à l'intérieur de celui-ci et téléchargez l'archive zip. Enfin décompressez la.

```bash
config_dir="/remplacez/par/le/votre"
mkdir -p "${config_dir}/custom_components"
cd !$
wget "<url_du_zip>" -O 'linky_tic_din.zip'
unzip 'linky_tic_din.zip'
mv 'lixeeticdin-<version_du_zip>' 'lixeeticdin'
```

Remplacez toutes les valeurs entre `<...>`.

Vous devriez maintenant avoir le dossier `/votre/config/dir/custom_components/lixeeticdin`.

### Activation et configuration dans Home Assistant

Ajoutez les lignes suivantes dans cotre configuration Home Assistant (`configuration.yaml`):

```yaml
lixeeticdin:
  serial_port: /dev/ttyUSB0
```

Redémarrez votre instance Home Assistant, attendez un peu, et recherchez le terme "linky" dans la liste de vos entités.

En cas de doutes, vérifiez les logs d'Home Assistant.

## Développement
### Disclaimer

Je ne suis ni un habitué du python et encore moins du framework Home Assistant ! Ce module doit donc être largement améliorable. Néanmoins il permet le support simple et natif d'un maximum d'éléments transmis par le compteur Linky dans Home Assistant au travers d'une connection série du TIC.

### Architecture

![Schéma d'architecture du module](https://github.com/hekmon/lixeeticdin/raw/v1.0.1/res/lixeeticdin_archi.excalidraw.png "Schéma d'architecture du module")

### Référence

Le document de référence du protocole TIC dévelopé par Enedis est [archivé dans ce repo](https://github.com/hekmon/lixeeticdin/raw/v1.0.1/Enedis-NOI-CPT_54E.pdf). Vous y trouverez toutes les informations nécessaire au dévelopement ainsi que des détails sur les informations remontées par ce plugin. Celui-ci n'est évidement pas couvert par la license MIT de ce repo et reste la propriété d'Enedis.
