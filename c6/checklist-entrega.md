# Checklist d'entrega

> Repassa-la **abans** de dir a un client que ja ho té. Cada punt d'aquesta
> llista és una trucada que t'estalvies a les vuit del vespre d'un divendres.

## 1. Maquinari i sistema

- [ ] `nvidia-smi` respon i la versió del driver és **≥ 570** si la GPU és RTX 50xx
- [ ] El driver sobreviu a un `apt upgrade` amb nucli nou (DKMS instal·lat i provat)
- [ ] Secure Boot: o desactivat conscientment, o el mòdul signat amb MOK
- [ ] La partició de dades té l'espai del disc de veritat (LVM ampliat)
- [ ] Espai lliure suficient: cada model són 5–20 GB i el client en voldrà més
- [ ] El servidor arrenca sol després d'un tall de llum, **sense teclat**
  (compte amb el xifratge de disc: demana la contrasenya per arrencar)

## 2. Serveis

- [ ] `systemctl is-enabled ollama docker` → `enabled` tots dos
- [ ] Els contenidors tenen `restart: unless-stopped`
- [ ] Els healthchecks estan definits i passen
- [ ] Reinici complet provat: `sudo reboot` i tot torna sol
- [ ] Els volums de Qdrant i Postgres són **volums**, no directoris temporals

## 3. Seguretat

- [ ] `ufw` actiu i **només** amb els ports que calen
- [ ] **Ollama NO exposat** a internet. Recorda: no té cap autenticació
- [ ] Si Ollama s'ha d'obrir a la LAN, és només a la subxarxa concreta
- [ ] L'API du autenticació (com a mínim una clau) i **no** és la d'exemple
- [ ] La base de dades: l'agent es connecta amb un rol de **només lectura**
- [ ] Aquest rol només té `GRANT SELECT` **sobre les vistes**, no sobre les taules
- [ ] Cap credencial al codi ni al control de versions. `.env` al `.gitignore`
- [ ] Contrasenyes canviades: cap `canvia_aquesta_contrasenya` en producció
- [ ] `fail2ban` actiu si el servidor toca internet

## 4. L'assistent

- [ ] Respon la pregunta de referència del client **creuant les fonts que toca**
- [ ] Cita les fonts, i les citacions apunten a documents que existeixen
- [ ] **Diu «no ho sé»** quan no ho sap: provat amb una referència inventada
- [ ] Els casos negatius de l'avaluació passen
- [ ] Temperatura entre 0 i 0,3
- [ ] El prompt del sistema és en català i el model respon en català sempre
- [ ] El text-to-SQL rebutja `DELETE`, `DROP` i les taules crues (provat, no suposat)
- [ ] Les eines d'API tenen timeout i reintents, i el cas «l'API cau» s'ha provat
- [ ] Límit de passos de l'agent: no es queda en bucle cridant eines

## 5. Dades i documents

- [ ] La ingesta és **reproduïble**: un `--reset` i torna a sortir igual
- [ ] Els documents escanejats o bé passen per OCR o bé estan **documentats com a exclosos**
- [ ] El client sap **quins documents hi ha indexats** i quins no
- [ ] Hi ha un procediment escrit per afegir un document nou
- [ ] Els documents amb dades personals estan identificats i tractats (RGPD)

## 6. Còpies de seguretat

- [ ] Còpia del volum de **Postgres** (les dades no es poden reconstruir)
- [ ] Còpia del volum de **Qdrant**, o el procediment per tornar a indexar
- [ ] Còpia dels **documents originals** (és l'única font de veritat)
- [ ] Còpia del `.env` en un lloc segur i **fora** del servidor
- [ ] **Restauració provada.** Una còpia que no s'ha restaurat mai no és una còpia

## 7. Monitoratge i manteniment

- [ ] Alerta si el servei d'Ollama cau
- [ ] Alerta d'espai en disc (els models i els registres creixen)
- [ ] Registre de preguntes i respostes, amb l'avís de RGPD corresponent
- [ ] Algú sap **quan** i **com** s'actualitza, i que un nucli nou pot trencar el driver
- [ ] Finestra de manteniment acordada, i mai un divendres

## 8. Documentació per al client

- [ ] Com engegar-ho i aturar-ho
- [ ] Com afegir o treure documents
- [ ] Què fer si no respon: els tres o quatre passos de diagnòstic
- [ ] **Què NO sap fer** l'assistent, per escrit. Gestionar l'expectativa és
      la meitat de la feina
- [ ] A qui es truca i amb quin abast de suport

## 9. Traspàs

- [ ] Una persona del client ha fet la instal·lació **amb tu mirant**, no al revés
- [ ] Aquesta persona ha afegit un document i l'ha vist aparèixer a les respostes
- [ ] Ha vist l'assistent equivocar-se, i sap que això passa i per què
- [ ] Té les credencials i sap on són les còpies

---

*CIDET · IA en local · Classe 6*
