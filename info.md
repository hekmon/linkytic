# Linky TIC - Support Linky dans Home Assistant

Cette intégration pour Home Assistant ajoute le support des Linky au travers de n'importe quelle connection série en provenance du module TIC (Télé Information Client) du compteur Linky.

Par exemple:

- [Module série USB développé par LiXee](https://lixee.fr/produits/30-tic-din-3770014375070.html) (celui que j'utilise)
- [Téléinfo 1 compteur USB rail DIN de Cartelectronic](https://www.cartelectronic.fr/teleinfo-compteur-enedis/17-teleinfo-1-compteur-usb-rail-din-3760313520028.html) (validé par un [utilisateur](https://github.com/hekmon/linkytic/issues/2#issuecomment-1364535337))
- [Circuit à faire soi-même](https://miniprojets.net/index.php/2019/06/28/recuperer-les-donnees-de-son-compteur-linky/), nécessitant peu de composants ([autre article avec un circuit similaire](https://hallard.me/pitinfov12/)). Validé par un [utilisateur](https://github.com/hekmon/linkytic/pull/4#issuecomment-1368877730).
- [Module Micro Téléinfo V3.0](https://github.com/hallard/uTeleinfo) à fabriquer soi-même ou pré-assemblé sur [Tindie](https://www.tindie.com/products/28873/)
- [Teleinfo ADTEK](https://doc.eedomus.com/view/T%C3%A9l%C3%A9info_USB_ADTEK) attention cependant [le baudrate ne semble pas standard](https://github.com/hekmon/linkytic/issues/40).
- et certainement bien d'autres ! (n'hésitez pas à m'ouvrir une issue pour rajouter le votre si vous avez validé que celui-ci fonctionne avec cette intégration afin d'aidez de potentiels futurs utilisateurs qui n'en auraient pas encore choisi un)

[Exemple sous Home Assistant](https://github.com/hekmon/linkytic/raw/v3.0.0-beta5/res/SCR-20221223-ink.png).

Théoriquement cette intégration est compatible avec les compteurs pré Linky qui possèdent un module TIC en choisissant le mode historique. Mais n'en ayant aucun dans mon entourage, je n'ai pas pu le vérifier.

## Informations remontées

Cette intégration va lire de manière continue les informations envoyées sur le TIC et stocker en mémoire la dernière valeur lue pour chacun des compteurs. Ensuite, Home Assistant viendra régulièrement lui même "récolter" les valeurs des différents sondes que l'intégration lui a déclaré. La fréquence observée semble être de 30 secondes. C'est largement suffisement pour la très grande majoritée des sondes.

Cependant, certaines sondes peuvent avoir de la valeur dans leur "instantanéité" (relative). Pour cela, l'intégration possède une option "temps réel" qui peut être activée. Celle-ci ne passera pas toutes les sondes en temps réel mais seulement celles pour qui cela peut avoir du sens (voir ci-dessous). Cette option temps réel notifiera Home Assistant qu'une nouvelle valeure est prête à être lue et lui demandera de venir la lire (et l'enregistrer) au plus vite à la différence des autres sondes dont les valeurs sont récupérées par Home Assistant, à son rythme.

Suivant la configuration que vous choisirez pour votre installation vous trouverez dans ce fichier dans la liste des sondes avec les annotations suivantes:

- <sup>1</sup> sonde compatible avec le mode temps réel: si celui-ci est activé par l'utilisateur, les mises à jours seront bien plus fréquentes (dès qu'elles sont lues sur la connection série)
- <sup>2</sup> sonde dont le mode temps réel est forcé même si l'utilisateur n'a pas activé le mode temps réèl dans le cas où la valeur de la sonde est importante et/ou éphémère

### Mode historique

Le mode historique est le plus commun (existant pré Linky) : il est activé par défault à moins que vous soyez producteur d'énergie.

#### Compteurs mono-phasé

Les 23 champs des compteurs mono-phasé configurés en mode historique sont supportés:

- `ADCO` Adresse du compteur (avec parsing EURIDIS en attributs étendus et périphérique agrégateur sous Home Assistant)
- `OPTARIF` Option tarifaire choisie
- `ISOUSC` Intensité souscrite
- `BASE` Index option Base
- `HCHC` Index option Heures Creuses - Heures Creuses
- `HCHP` Index option Heures Creuses - Heures Pleines
- `EJPHN` Index option EJP - Heures Normales
- `EJPHPM` Index option EJP - Heures de Pointe Mobile
- `BBRHCJB` Index option Tempo - Heures Creuses Jours Bleus
- `BBRHPJB` Index option Tempo - Heures Pleines Jours Bleus
- `BBRHCJW` Index option Tempo - Heures Creuses Jours Blancs
- `BBRHPJW` Index option Tempo - Heures Pleines Jours Blancs
- `BBRHCJR` Index option Tempo - Heures Creuses Jours Rouges
- `BBRHPJR` Index option Tempo - Heures Pleines Jours Rouges
- `PEJP` Préavis Début EJP (30 min)
- `PTEC` Période Tarifaire en cours
- `DEMAIN` Couleur du lendemain
- `IINST` Intensité Instantanée <sup>1</sup>
- `ADPS` Avertissement de Dépassement De Puissance Souscrite <sup>2</sup>
- `IMAX` Intensité maximale appelée
- `PAPP` Puissance apparente <sup>1</sup>
- `HHPHC` Horaire Heures Pleines Heures Creuses
- `MOTDETAT` Mot d'état du compteur

#### Compteurs tri-phasés

⚠️ Actuellement en beta ⚠️

Des retours de log en `DEBUG` pendant l'émission de trames courtes sont nécessaires pour valider le bon fonctionnement de l'intégration sur ces compteurs, n'hésitez pas à ouvrir une [issue](https://github.com/hekmon/linkytic/issues) si vous avec un compteur triphasé pour aider à sa finalisation !

- `ADCO` Adresse du compteur (avec parsing EURIDIS en attributs étendus et périphérique agrégateur sous Home Assistant)
- `OPTARIF` Option tarifaire choisie
- `ISOUSC` Intensité souscrite
- `BASE` Index option Base
- `HCHC` Index option Heures Creuses - Heures Creuses
- `HCHP` Index option Heures Creuses - Heures Pleines
- `EJPHN` Index option EJP - Heures Normales
- `EJPHPM` Index option EJP - Heures de Pointe Mobile
- `BBRHCJB` Index option Tempo - Heures Creuses Jours Bleus
- `BBRHPJB` Index option Tempo - Heures Pleines Jours Bleus
- `BBRHCJW` Index option Tempo - Heures Creuses Jours Blancs
- `BBRHPJW` Index option Tempo - Heures Pleines Jours Blancs
- `BBRHCJR` Index option Tempo - Heures Creuses Jours Rouges
- `BBRHPJR` Index option Tempo - Heures Pleines Jours Rouges
- `PEJP` Préavis Début EJP (30 min)
- `PTEC` Période Tarifaire en cours
- `DEMAIN` Couleur du lendemain
- `IINST1` Intensité Instantanée (phase 1) <sup>1</sup> pour les trames longues <sup>2</sup> pour les trames courtes
- `IINST2` Intensité Instantanée (phase 2) <sup>1</sup> pour les trames longues <sup>2</sup> pour les trames courtes
- `IINST3` Intensité Instantanée (phase 3) <sup>1</sup> pour les trames longues <sup>2</sup> pour les trames courtes
- `IMAX1` Intensité maximale (phase 1)
- `IMAX2` Intensité maximale (phase 2)
- `IMAX3` Intensité maximale (phase 3)
- `PMAX` Puissance maximale triphasée atteinte
- `PAPP` Puissance apparente <sup>1</sup>
- `HHPHC` Horaire Heures Pleines Heures Creuses
- `MOTDETAT` Mot d'état du compteur
- `ADIR1` Avertissement de Dépassement d'intensité de réglage (phase 1) <sup>2</sup> trames courtes uniquement
- `ADIR2` Avertissement de Dépassement d'intensité de réglage (phase 2) <sup>2</sup> trames courtes uniquement
- `ADIR3` Avertissement de Dépassement d'intensité de réglage (phase 3) <sup>2</sup> trames courtes uniquement

### Mode standard

Le mode standard peut être considéré comme la "v2" du TIC développé par Enedis et a été introduit avec les Linky. Il transmets plus d'informations mais n'est activé qu'à la demande de l'utilisateur ou si celui-ci est producteur d'énergie. Le mode standard n'est pour le moment pas supporté même si j'envisage d'y passer moi même pour pouvoir le développer. Le coeur du module (lecture série du TIC) est théoriquement déjà compatible avec ce mode mais pas les entités Home Assistant (voir la partie Architecture).

## Installation

Une fois Home Assistant redémarré, allez dans: `Paramètres -> Appareils et services -> Ajouter une intégration`. Dans la fenêtre modale qui s'ouvre, cherchez `linky` et sélectionnez l'intégration s'appelant `Linky TIC` dans la liste (une petite icône d'un carton ouvert avec un texte de survol indiquant `Fourni par une extension personnalisée` devrait se trouver sur la droite).

Vous devriez passer sur le formulaire d'installation vous présentant les 3 champs suivants:

- `Chemin/Adresse vers le périphérique série` Ici renseignez le path de votre périphérique USB testé précédement. Le champ est rempli par default avec la valeur `/dev/ttyUSB0`: Il ne s'agit pas d'une auto détection mais simplement de la valeure la plus probable dans 99% des installations. Il est aussi possible d'utiliser une URL supporté par [pyserial](https://pyserial.readthedocs.io/en/latest/url_handlers.html), ce qui peut s'avérer utile si le port série est connecté sur un appareil distant (support de la rfc2217 par exemple).
- `Mode TIC` Choississez entre `Standard` et `Historique`. Plus de détails sur ces 2 modes en début de ce document.
- `Triphasé` À cocher si votre compteur est un compteur... triphasé. À noter que cette option n'a d'effet que si vous êtes en mode historique (le mode standard gère le mono et le tri de manière indifférente).

Validez et patientez pendant le temps du test. Celui-ci va tenter d'ouvrir une connection série sur le périphérique désigné et d'y lire au moins une ligne. En cas d'erreur, celle-ci vous sera retourné à l'écran de configuration. Sinon, votre nouvelle intégration est prête et disponible dans la liste des intégrations de la page où vous vous trouvez.

Pour ceux intéressé par le mode "temps réel", localisez l'intégration Linky TIC dans les tuiles de la page et cliquez sur `Configurer`.

## Développement

### Disclaimer

Je ne suis pas un habitué du python et encore moins du framework Home Assistant ! Ce module doit donc être largement améliorable. Néanmoins il permet le support simple et natif d'un maximum d'éléments transmis par le compteur Linky dans Home Assistant au travers d'une connection série du TIC dont certains en temps réel.

### Architecture

![Schéma d'architecture du module](https://github.com/hekmon/linkytic/raw/v3.0.0-beta5/res/linkytic_archi.excalidraw.png "Schéma d'architecture du module")

### Référence

Le document de référence du protocole TIC dévelopé par Enedis est [archivé dans ce repo](https://github.com/hekmon/linkytic/raw/v3.0.0-beta5/res/Enedis-NOI-CPT_54E.pdf). Vous y trouverez toutes les informations nécessaire au dévelopement ainsi que des détails sur les informations remontées par ce plugin. Celui-ci et tout autre document de référence d'implémentation pouvant se trouver dans ce répertoire ne sont évidement pas couvert par la license MIT de ce repo et reste la propriété de leurs auteurs respectifs.
