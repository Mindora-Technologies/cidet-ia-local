# Configurar el servei d'Ollama

Ollama s'instal·la amb valors conservadors que van bé a un portàtil. En un
servidor per a una empresa, n'hi ha sis que val la pena canviar. Es fan tots amb
un *override* de systemd, que no toca el fitxer original del paquet i sobreviu a
les actualitzacions.

```bash
sudo systemctl edit ollama
```

S'obre un editor buit. Escriu-hi això:

```ini
[Service]
Environment="OLLAMA_HOST=0.0.0.0"
Environment="OLLAMA_KEEP_ALIVE=-1"
Environment="OLLAMA_FLASH_ATTENTION=1"
Environment="OLLAMA_KV_CACHE_TYPE=q8_0"
Environment="OLLAMA_NUM_PARALLEL=2"
Environment="OLLAMA_MAX_LOADED_MODELS=2"
```

```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama
systemctl show ollama -p Environment      # comprova que hi són
```

## Què fa cada una

| Variable | Què guanyes | Què et costa |
|---|---|---|
| `OLLAMA_HOST=0.0.0.0` | Escolta a totes les interfícies: hi pots arribar des d'un altre ordinador. Per defecte només escolta a `127.0.0.1`. | **Queda obert a qui pugui arribar al port.** Llegeix la secció de xarxa d'aquí sota abans de deixar-ho així. |
| `OLLAMA_KEEP_ALIVE=-1` | El model es queda a la VRAM per sempre. Sense això marxa als 5 minuts i la primera pregunta següent triga uns quants segons a carregar-lo. | La VRAM queda ocupada encara que ningú faci servir el model. Amb una sola targeta, això vol dir que no en pots fer servir cap altre. |
| `OLLAMA_FLASH_ATTENTION=1` | Càlcul de l'atenció més eficient: menys memòria per al context i una mica més de velocitat, sobretot amb contextos llargs. | Necessita una GPU prou moderna. En targetes antigues s'ignora o va pitjor. |
| `OLLAMA_KV_CACHE_TYPE=q8_0` | Quantitza la KV cache a 8 bits: **la meitat de VRAM per al context**. Amb 16k de context són uns quants GB de diferència. | Una pèrdua de qualitat molt petita, però no nul·la. Requereix flash attention activat. |
| `OLLAMA_NUM_PARALLEL=2` | Dues peticions alhora contra el mateix model, en comptes de fer cua. | Cada petició paral·lela necessita la seva KV cache: més VRAM. Amb 2 ja es nota; posar-hi 8 en una targeta de 12 GB no acaba bé. |
| `OLLAMA_MAX_LOADED_MODELS=2` | Dos models diferents a la VRAM alhora, útil si en tens un de xat i un d'embeddings. | Han de cabre-hi **tots dos a la vegada**. Si no hi caben, Ollama en descarrega un i tornes a pagar la càrrega. |

> Les tres primeres són gairebé sempre bona idea en un servidor.
> `NUM_PARALLEL` i `MAX_LOADED_MODELS` depenen de quanta VRAM et sobra: fes els
> números amb `c1/hardware-calc.xlsx` abans de pujar-los.

## La regla de xarxa

**Ollama no té cap autenticació.** Ni usuari, ni contrasenya, ni clau d'API. Qui
arribi al port 11434 pot fer servir els teus models, veure quins en tens i
mantenir-te la GPU ocupada. Amb `OLLAMA_HOST=0.0.0.0` acabes de treure la porta.

Per això el port s'obre **només a la subxarxa local**, mai a internet:

```bash
sudo ufw allow from 192.168.X.0/24 to any port 11434 proto tcp
sudo ufw status verbose
```

> Substitueix `192.168.X.0/24` per la subxarxa real. A l'aula la mirarem amb
> `ip -4 addr show` i posarem la que toqui.

El que **no** has de fer mai:

```bash
sudo ufw allow 11434          # ← obert a tothom qui hi arribi
```

Si el servei ha de sortir de la xarxa local, no s'exposa Ollama: es posa al
davant un proxy amb clau d'API i registre de peticions. Ho veurem a la C6.

---

*CIDET · IA en local · Classe 2*
