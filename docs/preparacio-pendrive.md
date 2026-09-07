# Preparació dels suports físics (USB)

> **Per què això primer?** Els equips de l'aula arriben **sense sistema operatiu** i no
> podem dependre de la xarxa del centre per baixar 3 GB d'ISO ×3 màquines, ni 20 GB de
> models. Tot el que és pesat es baixa **abans**, es porta en USB i s'instal·la des d'allà.

---

## 0. Què necessites

| Element | Quantitat | Requisits |
|---|---|---|
| USB *booteable* d'Ubuntu Server | **3** | ≥ 8 GB cadascun (un per equip; es poden fer en paral·lel) |
| USB de **dades** | **1** | **≥ 64 GB**, formatat en **exFAT** |
| Cable de xarxa / accés a internet a l'aula | desitjable | només com a pla B |

> ⚠️ **exFAT, no FAT32.** La ISO d'Ubuntu i els fitxers `.gguf` superen els 4 GB i
> FAT32 no els admet. NTFS també val si només s'ha de llegir des de Linux, però exFAT
> funciona a Linux, macOS i Windows sense drames.

Abans de res, executa:

```bash
./scripts/00-descarrega-offline.sh
```

Això omple `./offline/` amb tot el material. Es pot parar i reprendre: les descàrregues
són reanudables i el script no torna a baixar el que ja hi és amb el hash correcte.

---

## 1. Crear l'USB *booteable* d'Ubuntu Server

L'ISO és **híbrida**: es escriu tal qual al dispositiu, no cal cap format previ.

### 1.1 Des de Linux (`dd`)

**Pas 1 — identifica el dispositiu correcte.** Aquest és l'únic pas que et pot arruïnar el dia.

```bash
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT,MODEL
```

Endolla l'USB, torna a executar-ho i mira **quin dispositiu ha aparegut de nou**.
Ha de ser un `/dev/sdX` **sencer** (p. ex. `/dev/sdb`), **no** una partició (`/dev/sdb1`).

> 🛑 **Comprova la mida.** Si veus `931,5G`, és el teu disc dur: pararia aquí.
> `dd` no pregunta res i no té desfer.

**Pas 2 — desmunta (que no és el mateix que expulsar):**

```bash
sudo umount /dev/sdb?* 2>/dev/null || true
```

**Pas 3 — escriu:**

```bash
sudo dd if=offline/iso/ubuntu-24.04.*-live-server-amd64.iso \
        of=/dev/sdb bs=4M status=progress conv=fsync
sync
```

Triga entre 3 i 10 minuts segons l'USB. Quan acabi, `sync` s'assegura que els búfers
s'han buidat de veritat abans de treure'l.

**Pas 4 — verifica (opcional però recomanat):**

```bash
# compara els primers N bytes escrits amb els de la ISO
ISO=offline/iso/ubuntu-24.04.*-live-server-amd64.iso
BYTES=$(stat -c%s $ISO)
sudo dd if=/dev/sdb bs=4M count=$((BYTES/4194304+1)) 2>/dev/null | head -c $BYTES | sha256sum
sha256sum $ISO
```

Els dos hashos han de coincidir.

### 1.2 Des de macOS

```bash
diskutil list                        # localitza el disc, p. ex. /dev/disk4
diskutil unmountDisk /dev/disk4
sudo dd if=ubuntu-24.04-live-server-amd64.iso of=/dev/rdisk4 bs=4m status=progress
diskutil eject /dev/disk4
```

> Fixa't en la **`r`** de `/dev/rdisk4` (raw): és molt més ràpid que `/dev/disk4`.

### 1.3 Des de Windows

Dues opcions, totes dues bé:

- **Rufus** (recomanat): tria la ISO, esquema de partició **GPT**, sistema destí **UEFI**.
  Quan pregunti *ISO Image mode* vs *DD Image mode*, accepta el mode recomanat (**ISO**).
- **balenaEtcher**: *Flash from file* → tria la ISO → tria l'USB → *Flash!*. Més simple,
  menys opcions, verifica automàticament.

> No facis servir "copiar i enganxar la ISO a l'USB": això no crea res arrencable.

---

## 2. Repartiment del contingut

### USB 1, 2 i 3 — *booteables* (un per equip)

Només l'ISO d'Ubuntu Server escrita amb `dd`/Rufus. Res més.

Etiqueta'ls físicament: `CIDET-UBUNTU-1`, `-2`, `-3`.

### USB 4 — dades (≥ 64 GB, exFAT)

Copia-hi **tota** la carpeta `offline/`:

```bash
# format exFAT (a Linux; canvia /dev/sdc1 pel teu)
sudo mkfs.exfat -n CIDET-DADES /dev/sdc1

# còpia amb progrés i possibilitat de reprendre
rsync -ah --info=progress2 offline/ /media/$USER/CIDET-DADES/offline/
sync
```

Contingut esperat:

```
offline/
├── iso/       ubuntu-24.04.x-live-server-amd64.iso  +  SHA256SUMS
├── nvidia/    NVIDIA-Linux-x86_64-<versió>.run       (≥ 570!)
├── docker/    nvidia_cuda_12.6.0-base-ubuntu24.04.tar
│              qdrant_qdrant_latest.tar
│              postgres_16.tar
│              ghcr.io_open-webui_open-webui_main.tar
├── models/    Qwen3-4B-Q4_K_M.gguf ... Qwen3-32B-Q4_K_M.gguf
├── ollama/    install.sh  +  ollama-linux-amd64.tgz
└── CHECKSUMS.txt
```

**Verificació al destí**, abans de començar la classe:

```bash
cd /media/$USER/CIDET-DADES/offline && sha256sum -c CHECKSUMS.txt
```

---

## 3. Fer servir el material al destí (sense internet)

### 3.1 Carregar les imatges Docker

`docker pull` no funcionarà sense xarxa. En comptes d'això:

```bash
cd /media/$USER/CIDET-DADES/offline/docker
for t in *.tar; do
  echo "→ $t"
  sudo docker load -i "$t"
done
sudo docker images        # comprova que hi són totes
```

`docker load` restaura la imatge amb el seu nom i etiqueta originals, així que els
`docker run` i els `docker-compose.yml` del curs funcionen sense canviar res.

### 3.2 Instal·lar Ollama sense xarxa

L'`install.sh` oficial baixa el binari d'internet. Amb el tarball ja baixat:

```bash
cd /media/$USER/CIDET-DADES/offline/ollama
sudo tar -C /usr -xzf ollama-linux-amd64.tgz
sudo useradd -r -s /bin/false -U -m -d /usr/share/ollama ollama || true
sudo tee /etc/systemd/system/ollama.service >/dev/null <<'UNIT'
[Unit]
Description=Ollama Service
After=network-online.target

[Service]
ExecStart=/usr/bin/ollama serve
User=ollama
Group=ollama
Restart=always
RestartSec=3
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable --now ollama
ollama --version
```

### 3.3 Importar un model GGUF a Ollama sense xarxa

`ollama pull` necessita internet; `ollama create` no. Per cada model:

```bash
cd /media/$USER/CIDET-DADES/offline/models

cat > Modelfile.qwen3-4b <<'MF'
FROM ./Qwen3-4B-Q4_K_M.gguf

PARAMETER temperature 0.2
PARAMETER num_ctx 8192

SYSTEM """Ets un assistent tècnic. Respon sempre en català, de manera concisa."""
MF

ollama create qwen3:4b -f Modelfile.qwen3-4b
ollama list
ollama run qwen3:4b "Digues 'hola' i res més."
```

> El fitxer `.gguf` es **copia** al magatzem d'Ollama (`/usr/share/ollama/.ollama`),
> així que després pots treure l'USB. Compta l'espai al disc del servidor: el doble
> mentre dura la importació.

El script `c1/pull-models.sh --offline /media/$USER/CIDET-DADES/offline/models`
fa tot això automàticament per a tots els models de cop.

---

## 4. Checklist final de la motxilla

Marca-ho tot abans de sortir de casa:

**Suports**
- [ ] 3 × USB booteables d'Ubuntu Server 24.04, etiquetats i **provats** (arrenca almenys un)
- [ ] 1 × USB de dades ≥ 64 GB en **exFAT** amb `offline/` copiat sencer
- [ ] `sha256sum -c CHECKSUMS.txt` executat i **sense errors**

**Contingut crític**
- [ ] ISO Ubuntu Server 24.04 LTS amb SHA256 verificat
- [ ] Driver NVIDIA `.run` **versió ≥ 570** (RTX 5070 i 5060 Ti són Blackwell)
- [ ] 4 imatges Docker en `.tar`
- [ ] Com a mínim `Qwen3-4B-Q4_K_M.gguf` (els deures de la C1)
- [ ] Tarball i `install.sh` d'Ollama

**Ferramenta física**
- [ ] Teclat + ratolí USB (els equips arriben pelats)
- [ ] Monitor + cable **HDMI i DisplayPort** (no saps quin port tindrà lliure la GPU)
- [ ] Cable de xarxa RJ-45 i, si pot ser, un switch petit
- [ ] Regleta d'endolls
- [ ] Adaptador USB-C ↔ USB-A

**Paper / digital**
- [ ] `c1/install-server.md` imprès o al portàtil (per si el projector falla)
- [ ] `c1/hardware-calc.xlsx` copiat a l'USB de dades per repartir-lo
- [ ] Credencials de BIOS dels equips, si en tenen

**Pla B**
- [ ] Compartir internet des del mòbil configurat i provat
- [ ] Els models també al portàtil del formador, per si un USB peta

---

*CIDET · IA en local · Classe 1*
