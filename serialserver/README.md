# Connexion serial distante

Dans le cas ou votre module de connection série/USB ne peut pas être branché directement sur la machine hébergeant Home Assistant, vous avez toujours la possibilité de transférer par le réseau la connection série au travers du protocole défini par la RFC 2217.

Le code du serveur (`rfc2217_server.py`) n'est pas le miens mais est celui du projet `pyserial` (vous pouvez trouver l'original [ici](https://github.com/pyserial/pyserial/blob/v3.4/examples/rfc2217_server.py)) proposant la bibliothèque utilisée pour construire le module Home Assistant. Je ne propose ici qu'une mise en oeuvre de ce dernier.

# Installation

## Machine avec le module série

Validez que vous avez bien votre module série d'accessible:
```raw
hekmon@nucsrv:~$ ls -l /dev/ttyUSB0
crw-rw---- 1 root dialout 188, 0 Jun  4 11:55 /dev/ttyUSB0
hekmon@nucsrv:~$
```

Commencez par créer un utilisateur qui sera utilisé pour faire tourner le server:
```bash
sudo useradd --groups dialout --home-dir /usr/lib/serial --create-home --system --shell /usr/sbin/nologin serial
```

Copier les fichiers de ce dossier sur la machine cible:
```raw
/usr/lib/serial/rfc2217_server.py
/etc/systemd/system/serialrfc2217server.service
/etc/serialrfc2217server
```

Une fois l'utilisateur créé et les fichiers copiés, lancez le serveur comme ceci:
```bash
# Enregistrement du nouveau service
sudo systemctl daemon-reload
# Activation du service au (re)démarrage
sudo systemctl enable serialrfc2217server.service
# Démarage du service manuellement
sudo systemctl start serialrfc2217server.service
# Vérification des logs du service en temps réèl
sudo journalctl -f -u serialrfc2217server.service
```

Votre machine serveur est prête ! Pour la suite, admettons que l'IP de votre machine où votre module série et le serveur réseau est possède l'IP `192.168.1.140` et que vous n'avez pas changé le port `2217` par défault du fichier `/etc/serialrfc2217server`.

# Machine hébergeant Home Assistant

Suivez l'installation normale du module, seulement au moment d'entrer l'adresse du module série à la configuration de l'integration sous Home Assistant utilisez l'adresse suivante: `rfc2217://192.168.1.140:2217` en prenant soin de bien remplacer l'adresse IP par celle de votre machine hébergeant le module série et votre serveur. Si vous avez laissez la vérification des logs du service en temps réèl sur l'autre machine vous devriez voir une connection arriver ! Et le module Linky TIC accepter votre module série lu au travers de votre réseau.
