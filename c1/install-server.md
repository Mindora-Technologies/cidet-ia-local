# Instal·lació del servidor d'IA local

> **Per a qui és això.** Per a tu, avui, a l'aula — i sobretot per a d'aquí a tres
> setmanes, quan siguis a casa d'un client amb una torre nova i sense ningú a qui
> preguntar. Cada pas porta el *què* i el *per què*.
>
> **Temps estimat:** 75 minuts si tot va bé. Compta'n 120 la primera vegada.
>
> **Punt de partida:** una màquina amb GPU NVIDIA, sense sistema operatiu, i l'USB
> preparat segons [`docs/preparacio-pendrive.md`](../docs/preparacio-pendrive.md).

---

## Índex

1. [Instal·lació d'Ubuntu Server 24.04](#1-installació-dubuntu-server-2404)
2. [Primers passos al sistema](#2-primers-passos-al-sistema)
3. [Driver NVIDIA](#3-driver-nvidia)
4. [CUDA toolkit](#4-cuda-toolkit)
5. [Docker + NVIDIA Container Toolkit](#5-docker--nvidia-container-toolkit)
6. [Ollama](#6-ollama)
7. [Comprovació final](#7-comprovació-final)
8. [Errors freqüents](#8-errors-freqüents)

---

## 1. Instal·lació d'Ubuntu Server 24.04

### Per què Server i no Desktop?

| | Server | Desktop |
|---|---|---|
| Superfície d'atac | Mínima: ni navegador, ni ofimàtica, ni Bluetooth | Centenars de paquets que no faràs servir |
| RAM en repòs | ~400 MB | 1,5–2,5 GB |
| VRAM en repòs | **0 MB** | 300–600 MB que li roba l'escriptori al model |
| Administració | SSH, reproduïble, scriptable | Ratolí i pantalla |
| Actualitzacions | Menys paquets, menys reinicis | Més superfície, més trencadisses |

Aquests 300–600 MB de VRAM no són una anècdota: són la diferència entre que un
model de 14B en Q4 hi càpiga o no en una GPU de 12 GB.

> Si el client insisteix a tenir escriptori, instal·la Server i afegeix-hi
> després un entorn mínim (`xfce4`), però mai el Desktop sencer amb GNOME.

### 1.1 Arrencar des de l'USB

1. Endolla l'USB *booteable* i encén l'equip.
2. Entra a la BIOS/UEFI (`F2`, `Del`, `F12` o `Esc` segons la placa).
3. Comprova o ajusta:
   - **Secure Boot**: apunta si està actiu. Ho necessitaràs al pas 3.
   - **Boot mode**: UEFI (no Legacy/CSM).
   - **Above 4G Decoding**: activat, si l'opció hi és. Cal per a GPU amb molta VRAM.
   - **Resizable BAR**: activat, si l'opció hi és.
4. Arrenca des de l'USB → *Try or Install Ubuntu Server*.

### 1.2 Decisions durant l'instal·lador

| Pantalla | Què triar | Per què |
|---|---|---|
| Idioma de l'instal·lador | English | Els missatges d'error en anglès es poden cercar; en català, no. |
| Distribució de teclat | Spanish o Catalan | Que el `|` i el `-` surtin on toca quan escriguis contrasenyes. |
| Tipus d'instal·lació | **Ubuntu Server** (no *minimized*) | La *minimized* treu eines que després trobaràs a faltar. |
| Xarxa | DHCP ara; **IP fixa** en producció | El servidor ha de ser a la mateixa adreça sempre. |
| Proxy | Buit (llevat que el client en tingui) | — |
| Mirror | El que proposi | — |
| Disc | **Use an entire disk** + **Set up this disk as an LVM group** | LVM et deixa ampliar, moure i fer *snapshots* sense reinstal·lar. Els models ocupen molt i creixen. |
| Xifratge (LUKS) | **Segons el client** | Si el servidor és en un CPD amb control d'accés, no cal. Si és en un magatzem o pot sortir de l'edifici, **sí**. Compte: en arrencar demanarà la contrasenya per teclat → sense escriptori remot no arrenca sol. |
| Mida de la partició | **Amplia-la al màxim del disc** | L'instal·lador per defecte reserva només ~100 GB del volum LVM. Cada model són 5–20 GB. |
| Perfil | Usuari admin normal + contrasenya forta | Mai treballis com a root. |
| **Install OpenSSH server** | ✅ **SÍ** | Sense això et quedes lligat a la pantalla física. És l'error més car de tots. |
| Snaps suggerits | **Cap** | Docker per snap dóna problemes amb la GPU. L'instal·larem des del repo oficial. |

> **Sobre la mida de la partició LVM.** A la pantalla de *Storage configuration*, quan
> vegis `ubuntu-lv` amb una mida molt inferior a la del disc, selecciona'l → *Edit* →
> posa-hi tot l'espai disponible. Si te n'oblides, es pot arreglar després amb
> `sudo lvextend -l +100%FREE /dev/ubuntu-vg/ubuntu-lv && sudo resize2fs /dev/ubuntu-vg/ubuntu-lv`.

En acabar: *Reboot Now*, treu l'USB quan t'ho digui, i entra amb el teu usuari.

---

## 2. Primers passos al sistema

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y htop nvtop git curl build-essential ufw fail2ban
sudo ufw allow OpenSSH && sudo ufw enable
```

Què acabes d'instal·lar i per què:

| Eina | Per a què serveix |
|---|---|
| `htop` | Monitor de CPU i RAM interactiu. El faràs servir per veure si el model ha caigut a CPU. |
| `nvtop` | El mateix però per a la GPU: ús, VRAM, temperatura i processos, en temps real. **És l'eina que més miraràs tot el curs.** |
| `git` | Per baixar el repo del curs i versionar les configuracions del client. |
| `curl` | Per baixar instal·ladors i per provar les API des de la terminal. |
| `build-essential` | Compilador i capçaleres C/C++. Necessari per compilar `llama.cpp` a la C2 i per compilar el mòdul del driver NVIDIA. |
| `ufw` | Tallafoc senzill. Un servidor d'IA amb Ollama exposat a la xarxa és una API sense autenticació oberta a tothom. |
| `fail2ban` | Bloqueja IP després de N intents de SSH fallits. Imprescindible si el servidor toca internet. |

> ⚠️ **`ufw enable` per SSH.** Si estàs connectat per SSH, executa **primer**
> `sudo ufw allow OpenSSH` i **després** `enable`. Si ho fas al revés, et quedes fora.
> La comanda avisa (*Command may disrupt existing ssh connections*): respon `y` només
> si ja has obert el port.

Comprova l'estat:

```bash
sudo ufw status verbose
```

Ha de mostrar `Status: active` i només la regla d'OpenSSH.

---

## 3. Driver NVIDIA

Aquest és el pas on es perd la gent. Llegeix-te'l sencer abans d'executar res.

### 3.1 Via recomanada: repositori d'Ubuntu

```bash
sudo ubuntu-drivers devices
```

Sortida típica:

```
vendor   : NVIDIA Corporation
model    : GB206 [GeForce RTX 5060 Ti]
driver   : nvidia-driver-570 - distro non-free recommended
driver   : nvidia-driver-535 - distro non-free
```

```bash
sudo ubuntu-drivers install
sudo reboot
```

Després del reinici:

```bash
nvidia-smi
```

### 3.2 🔴 Avís crític: RTX 50xx necessita driver ≥ 570

Les **RTX 5070** i **RTX 5060 Ti** de l'aula són **Blackwell**. Els drivers de la
branca 535 i anteriors **no coneixen aquest maquinari**: el sistema arrenca, però
`nvidia-smi` diu `No devices were found` o directament falla.

Com comprovar-ho a la sortida de `nvidia-smi`:

```
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 570.86.16    Driver Version: 570.86.16    CUDA Version: 12.8      |
+-----------------------------------------------------------------------------+
                 ^^^^^^^^^ aquest número ha de ser >= 570
```

Si `ubuntu-drivers devices` no ofereix cap 570+, tens dues sortides:

```bash
# a) afegir el PPA de drivers gràfics (necessita internet)
sudo add-apt-repository ppa:graphics-drivers/ppa
sudo apt update
sudo apt install -y nvidia-driver-570
sudo reboot

# b) instal·lar des del .run del pen drive  →  secció 3.4
```

### 3.3 Troubleshooting: Secure Boot

**Això passa de veritat a casa dels clients.** Instal·les el driver, reinicies, i
`nvidia-smi` respon:

```
NVIDIA-SMI has failed because it couldn't communicate with the NVIDIA driver.
```

El driver hi és, però el nucli es nega a carregar un mòdul sense signar.

**Diagnòstic:**

```bash
# el mòdul està instal·lat?
ls /lib/modules/$(uname -r)/updates/dkms/ | grep nvidia

# el nucli l'ha rebutjat?
dmesg | grep -i nvidia
# → "Loading of unsigned module is rejected"
# → "module verification failed: signature and/or required key missing"

# Secure Boot està actiu?
mokutil --sb-state
# → SecureBoot enabled
```

Confirmat: és Secure Boot.

#### Sortida A — desactivar Secure Boot a la BIOS (ràpida)

1. `sudo reboot`, entra a la BIOS (`Del`/`F2`).
2. *Security* → *Secure Boot* → **Disabled**. En algunes plaques cal posar abans
   *OS Type* a *Other OS*, o esborrar les claus de plataforma.
3. Desa i surt. Arrenca i comprova amb `nvidia-smi`.

És el camí de 2 minuts. Vàlid en un laboratori. Alguns clients amb polítiques de
seguretat no t'ho deixaran fer, i llavors:

#### Sortida B — signar el mòdul amb MOK (correcta)

*MOK* = *Machine Owner Key*: una clau teva que el firmware accepta com a vàlida.

```bash
# 1. Generar la parella de claus
sudo mkdir -p /root/mok && cd /root/mok
sudo openssl req -new -x509 -newkey rsa:2048 -keyout MOK.priv -outform DER \
     -out MOK.der -days 36500 -subj "/CN=NVIDIA driver signing/" -nodes

# 2. Registrar la clau pública al firmware
sudo mokutil --import MOK.der
# Demanarà una contrasenya d'un sol ús. APUNTA-LA: la necessites al pas 4.

# 3. Reiniciar
sudo reboot
```

**4. A l'arrencada** apareix una pantalla blava, *MOK Manager* (**MokManager**).
Aquesta pantalla només surt un cop i **caduca als 10 segons**: no et distreguis.

- *Enroll MOK* → *Continue* → *Yes* → escriu la contrasenya del pas 2 → *Reboot*.

> El teclat aquí és **americà**. Si la contrasenya duu símbols, comprova on cauen.
> Millor: fes servir una contrasenya només de lletres i números.

**5. Signar el mòdul i verificar:**

```bash
# comprova que la clau s'ha registrat
mokutil --list-enrolled | grep -i nvidia

# signar tots els mòduls del driver
for mod in $(find /lib/modules/$(uname -r) -name 'nvidia*.ko*'); do
  sudo /usr/src/linux-headers-$(uname -r)/scripts/sign-file sha256 \
       /root/mok/MOK.priv /root/mok/MOK.der "$mod"
done

sudo depmod -a
sudo modprobe nvidia
nvidia-smi
```

> Si fas servir DKMS (el cas normal amb els paquets d'Ubuntu), pots automatitzar
> la signatura per a futurs nuclis posant les claus a
> `/etc/dkms/framework.conf` amb `mok_signing_key=/root/mok/MOK.priv` i
> `mok_certificate=/root/mok/MOK.der`. Així cada actualització de nucli torna a
> signar sola.

### 3.4 Alternativa offline: instal·lar des del `.run`

Sense internet, amb el fitxer del pen drive:

```bash
# 1. Atura l'entorn gràfic si n'hi ha (a Server normalment no cal)
sudo systemctl isolate multi-user.target
# si tens gdm3/lightdm:
sudo systemctl stop gdm3 2>/dev/null || sudo systemctl stop lightdm 2>/dev/null || true

# 2. Posa el driver lliure a la llista negra (xoca amb el propietari)
echo -e "blacklist nouveau\noptions nouveau modeset=0" | \
  sudo tee /etc/modprobe.d/blacklist-nouveau.conf
sudo update-initramfs -u
sudo reboot

# 3. Instal·la (amb DKMS perquè es reconstrueixi sol a cada nucli nou)
cd /media/$USER/CIDET-DADES/offline/nvidia
sudo sh NVIDIA-Linux-x86_64-*.run --dkms --silent

# 4. Comprova
sudo reboot
nvidia-smi
```

> ⚠️ **El preu del `.run`.** Un driver instal·lat així **es trenca a cada
> actualització de nucli**: el sistema arrenca amb un nucli nou, el mòdul ja no hi és,
> i `nvidia-smi` deixa de funcionar. Per això la flag `--dkms`: DKMS recompila el
> mòdul automàticament. Si no la poses, hauràs de reinstal·lar el `.run` a mà cada cop.
>
> Amb `--dkms` també necessites els `linux-headers` del nucli instal·lats:
> `sudo apt install -y linux-headers-$(uname -r)`.

---

## 4. CUDA toolkit

```bash
sudo apt install -y nvidia-cuda-toolkit
nvcc --version
```

**Per què l'instal·lem si Ollama ja funciona sense?**

Ollama porta les seves pròpies llibreries CUDA dins del paquet: per fer-lo anar,
el *toolkit* no cal. L'instal·lem perquè:

- A la **C2** compilarem **`llama.cpp`** des del codi font amb suport CUDA, i el
  compilador `nvcc` és imprescindible.
- **vLLM** (que veurem com a alternativa a Ollama per a producció) el demana.
- `nvcc --version` és una comprovació ràpida i fiable que la cadena CUDA està sencera.

> La versió de CUDA que reporta `nvidia-smi` (a dalt a la dreta) és la **màxima
> suportada pel driver**; la de `nvcc --version` és la **instal·lada al sistema**.
> Que no coincideixin és normal i no és cap error.

---

## 5. Docker + NVIDIA Container Toolkit

### 5.1 Docker des del repositori oficial

No facis servir `apt install docker.io` ni el snap: van endarrerits i el snap dóna
problemes amb els dispositius de la GPU.

```bash
# claus i repositori
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io \
                    docker-buildx-plugin docker-compose-plugin

# poder executar docker sense sudo
sudo usermod -aG docker $USER
newgrp docker      # o tanca i torna a obrir la sessió

docker run --rm hello-world
```

### 5.2 NVIDIA Container Toolkit

Sense això, un contenidor **no veu la GPU**, encara que el driver de l'amfitrió
funcioni perfectament.

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt update
sudo apt install -y nvidia-container-toolkit

sudo nvidia-ctk runtime configure --runtime=docker && sudo systemctl restart docker
```

**La prova de foc:**

```bash
docker run --rm --gpus all nvidia/cuda:12.6.0-base-ubuntu24.04 nvidia-smi
```

Ha de mostrar la teva GPU **des de dins del contenidor**. Si això funciona, ja
pots executar Qdrant, vLLM o el que vulgui GPU sense sorpreses.

### 5.3 Variant offline

```bash
cd /media/$USER/CIDET-DADES/offline/docker
for t in *.tar; do docker load -i "$t"; done
docker images
docker run --rm --gpus all nvidia/cuda:12.6.0-base-ubuntu24.04 nvidia-smi
```

> El **NVIDIA Container Toolkit** sí que s'ha d'instal·lar des de paquets. Si no
> tens xarxa, baixa'ls abans amb `apt download nvidia-container-toolkit
> libnvidia-container1 libnvidia-container-tools nvidia-container-toolkit-base`
> i porta els `.deb` al pen drive: `sudo dpkg -i *.deb`.

---

## 6. Ollama

### 6.1 Instal·lació amb xarxa

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama --version
```

L'instal·lador detecta la GPU, instal·la el binari a `/usr/local/bin` i deixa un
servei systemd actiu. Comprova-ho:

```bash
systemctl status ollama --no-pager
journalctl -u ollama -n 20 --no-pager | grep -i 'cuda\|gpu'
```

Als registres ha de sortir alguna cosa com `inference compute ... library=cuda`.
Si diu `library=cpu`, la GPU no s'està fent servir: torna al pas 3.

El primer model:

```bash
ollama pull qwen3:4b
ollama run qwen3:4b "Explica'm en dues frases què és la VRAM."
```

Mentre respon, en una altra terminal:

```bash
nvtop
```

Has de veure la VRAM ocupada i el nucli de la GPU al 90–100 %. **Aquesta és la
imatge que has de recordar**: si la GPU està al 0 % i la CPU al 100 %, el model
s'està executant per programari i anirà 20 vegades més lent.

### 6.2 Variant offline

Instal·lació del binari (vegeu `docs/preparacio-pendrive.md` §3.2) i després,
per cada model del pen drive:

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
```

O, per a tots de cop:

```bash
./c1/pull-models.sh --offline /media/$USER/CIDET-DADES/offline/models
```

### 6.3 Exposar Ollama a la xarxa (opcional, amb compte)

Per defecte Ollama només escolta a `127.0.0.1`. Per obrir-lo a la LAN:

```bash
sudo systemctl edit ollama
```

```ini
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
```

```bash
sudo systemctl daemon-reload && sudo systemctl restart ollama
sudo ufw allow from 192.168.1.0/24 to any port 11434 proto tcp
```

> 🔴 **Ollama no té autenticació.** Qui arribi al port 11434 pot fer servir els teus
> models, veure què hi tens i saturar-te la GPU. Obre'l **només** a la subxarxa que
> toca — mai amb `ufw allow 11434` a seques, i mai cap a internet. A la C6 hi posem
> un proxy amb clau al davant.

---

## 7. Comprovació final

Marca-ho tot. Si algun punt falla, no continuïs: el que ve després no funcionarà.

- [ ] **`nvidia-smi` respon** i mostra la GPU, amb `Driver Version` ≥ 570 si és una RTX 50xx
- [ ] **`nvtop` s'obre** i mostra la VRAM total correcta (12 GB / 16 GB)
- [ ] **`nvcc --version`** respon amb una versió de CUDA
- [ ] **`docker run --rm hello-world`** funciona **sense `sudo`**
- [ ] **`docker run --rm --gpus all nvidia/cuda:12.6.0-base-ubuntu24.04 nvidia-smi`** mostra la GPU des del contenidor
- [ ] **`ollama --version`** respon
- [ ] **`ollama list`** mostra almenys `qwen3:4b`
- [ ] **`ollama run qwen3:4b "hola"`** respon i, mentrestant, `nvtop` mostra activitat **a la GPU**
- [ ] **`sudo ufw status`** mostra `active` i **només** la regla d'OpenSSH
- [ ] **`systemctl is-enabled ollama docker`** diu `enabled` per als dos (sobreviuen al reinici)
- [ ] **`sudo reboot`** i tot torna a funcionar sense tocar res

Script de comprovació ràpida:

```bash
#!/usr/bin/env bash
set -uo pipefail
echo "── Comprovació del servidor ──"
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader \
  || echo "✘ nvidia-smi"
nvcc --version 2>/dev/null | tail -1 || echo "✘ nvcc"
docker run --rm --gpus all nvidia/cuda:12.6.0-base-ubuntu24.04 nvidia-smi -L \
  || echo "✘ GPU dins de Docker"
ollama list || echo "✘ ollama"
sudo ufw status | head -3
```

---

## 8. Errors freqüents

| Símptoma | Causa | Solució |
|---|---|---|
| `NVIDIA-SMI has failed because it couldn't communicate with the NVIDIA driver` | Secure Boot bloqueja el mòdul sense signar | §3.3: desactiva Secure Boot o signa amb MOK |
| `nvidia-smi` diu `No devices were found` amb una RTX 50xx | Driver < 570: no coneix Blackwell | Instal·la la branca 570+ (PPA o `.run` del pen drive) |
| Després d'`apt upgrade` la GPU desapareix | Nucli nou i mòdul no recompilat | `sudo apt install -y linux-headers-$(uname -r) && sudo dkms autoinstall` |
| `docker: Error response from daemon: could not select device driver "" with capabilities: [[gpu]]` | Falta el NVIDIA Container Toolkit o `nvidia-ctk runtime configure` | §5.2, i **reinicia Docker** |
| `permission denied while trying to connect to the Docker daemon socket` | L'usuari no és al grup `docker` | `sudo usermod -aG docker $USER` i torna a entrar (`newgrp docker`) |
| Ollama respon, però lentíssim, i `nvtop` mostra la GPU al 0 % | S'executa a CPU | `journalctl -u ollama | grep library` → si diu `cpu`, el driver no està bé |
| `Error: model requires more system memory than is available` | El model no cap ni amb offload | Baixa de quantització o de mida. Fes servir `c1/hardware-calc.xlsx`. |
| El model carrega però la resposta es talla a mitges | `num_ctx` massa gran per a la VRAM | Baixa el context o quantitza la KV cache a Q8 |
| `ollama pull` es queda a 0 % | Tallafoc o proxy del client | Fes servir la via offline amb GGUF (§6.2) |
| Es queda sense espai a `/` amb el disc mig buit | LVM no ampliat durant la instal·lació | `sudo lvextend -l +100%FREE /dev/ubuntu-vg/ubuntu-lv && sudo resize2fs /dev/ubuntu-vg/ubuntu-lv` |
| SSH deixa de respondre just després d'activar `ufw` | `ufw enable` sense `allow OpenSSH` | Pantalla i teclat físics: `sudo ufw allow OpenSSH` |
| `nouveau` es carrega i el driver propietari no | Falta la llista negra | §3.4, pas 2, i `sudo update-initramfs -u` |
| MokManager no apareix a l'arrencada | La pantalla caduca en 10 s, o UEFI la salta | Torna a fer `mokutil --import` i estigues atent al reinici |

---

## Deures per a la propera classe

1. Deixa el servidor engegat i accessible per SSH.
2. Executa `./c1/pull-models.sh` per tenir els models de la C2 baixats.
3. Obre `c1/hardware-calc.xlsx` i **dimensiona un cas real d'un client teu**:
   quin model faries servir, en quina GPU, amb quant context. Ho comentem a la C2.

---

*CIDET · IA en local · Classe 1*
