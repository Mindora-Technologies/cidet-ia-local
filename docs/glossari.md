# Glossari

Els termes que van sortint al curs, per ordre alfabètic. Està pensat per
consultar-lo quan et perdis enmig d'una explicació, no per llegir-lo seguit.

Entre parèntesis hi ha el terme en anglès quan és el que se sent a la pràctica,
perquè és el que trobaràs a la documentació i als fòrums.

[A](#a) · [B](#b) · [C](#c) · [D](#d) · [E](#e) · [F](#f) · [G](#g) · [H](#h) ·
[I](#i) · [K](#k) · [L](#l) · [M](#m) · [N](#n) · [O](#o) · [P](#p) · [Q](#q) ·
[R](#r) · [S](#s) · [T](#t) · [V](#v)

---

## A

**Agent**
Un sistema que **decideix** quines eines fa servir i en quin ordre, en comptes
de seguir sempre els mateixos passos. Un RAG clàssic sempre cerca i respon; un
agent pot mirar la base de dades, veure que li falta context i anar a buscar-lo.
Ho veurem a la C5.

**Al·lucinació** *(hallucination)*
Quan el model respon amb seguretat una cosa que no és certa. No és que menteixi:
està continuant text plausible, que és l'única cosa que sap fer. Es combat amb
RAG, instruccions de negativa i avaluació amb casos que ha de rebutjar.

**Amplada de banda de memòria** *(memory bandwidth)*
Quants GB per segon pot llegir la GPU de la seva pròpia memòria. **És el que
determina la velocitat de generació**, més que la potència de càlcul: per
escriure cada token, la GPU s'ha de llegir el model sencer.

**AWQ**
Mètode de quantització a 4 bits pensat per a servidors com vLLM. Protegeix els
pesos més importants perquè la pèrdua de qualitat sigui menor. A Ollama no es
fa servir: allà el format és GGUF.

## B

**Base de dades vectorial**
Una base de dades que desa embeddings i sap trobar els més semblants a un de
donat, ràpid. Al curs fem servir **Qdrant**. Ho veurem a la C4.

**Batching**
Agrupar diverses peticions per calcular-les juntes. Com que el coll d'ampolla
és llegir el model de la memòria, atendre'n vuit alhora costa molt menys que
vuit vegades una.

**BM25**
Algorisme de cerca per paraules, de toda la vida. No entén significats, però
troba **coincidències exactes** —una referència com `REF-1001`— molt millor que
els embeddings. Per això es combinen (cerca híbrida).

## C

**CUDA**
La plataforma de càlcul de NVIDIA. És el que permet que un model s'executi a la
GPU. Ollama porta les seves pròpies llibreries; el *toolkit* sencer només cal si
compiles alguna cosa.

**Cerca híbrida** *(hybrid search)*
Combinar la cerca per embeddings amb la cerca per paraules (BM25) i fusionar els
dos rànquings. Guanya en els casos on cadascuna sola falla. Ho veurem a la C5.

**Citació de fonts**
Que la resposta digui d'on ha tret cada cosa. No és un adorn: és l'única manera
que l'usuari pugui comprovar-ho, i la diferència entre una eina de feina i una
que no et pots creure.

**Context length** *(finestra de context)*
Quants tokens pot tenir el model «al davant» alhora: la pregunta, la conversa
anterior i els fragments que li has passat. Es configura amb `num_ctx` i **es
paga en VRAM**.

**Continuous batching**
Millora del *batching*: en comptes d'esperar que acabi tot el lot, les peticions
noves entren i les acabades surten sobre la marxa. És el que fa vLLM i el motiu
que aguanti tants usuaris alhora.

## D

**Decode**
La segona fase de la inferència: generar la resposta token a token. Va limitada
per l'amplada de banda i és la que marca els **tokens per segon**. Compara-la
amb *prefill*.

**Docker**
Empaqueta una aplicació amb tot el que necessita perquè funcioni igual a
qualsevol màquina. Al curs l'utilitzem per a Qdrant, Postgres i Open WebUI.

**Driver NVIDIA**
El programari que fa que el sistema operatiu vegi la GPU. Per a les targetes
RTX 50xx cal la versió **570 o superior**. Ho vam veure a la C1.

## E

**Embedding**
Un text convertit en una llista de números que representa el seu significat.
Dos textos que volen dir el mateix tenen embeddings pròxims, encara que no
comparteixin ni una paraula. És el que fa possible el RAG.

## F

**Flash attention**
Una manera més eficient de calcular l'atenció: menys memòria i una mica més de
velocitat, sobretot amb contextos llargs. A Ollama s'activa amb
`OLLAMA_FLASH_ATTENTION=1`.

**FP16**
Els pesos en 16 bits, **2 bytes per paràmetre**. És la referència de qualitat i
el punt de partida per calcular quant ocuparà un model quantitzat.

**Fragmentació** *(chunking)*
Partir els documents en trossos abans d'indexar-los. Massa petits perden el
context; massa grans barregen temes i la cerca perd punteria. Ho veurem a la C4.

## G

**GGUF**
El format de fitxer de model que fan servir Ollama i llama.cpp. Un sol fitxer
que porta els pesos ja quantitzats i la configuració. És el que trobaràs a
Hugging Face per executar en local.

**GPTQ**
Un altre mètode de quantització a 4 bits, del món de les GPU de servidor. Com
l'AWQ: el veuràs amb vLLM, no amb Ollama.

## H

**HNSW**
L'estructura d'índex que fa servir Qdrant per trobar els vectors més semblants
sense comparar-los tots. Sacrifica una mica de precisió a canvi de moltíssima
velocitat.

## I

**Inferència** *(inference)*
Executar un model ja entrenat per obtenir una resposta. És tot el que fem en
aquest curs: no entrenem res, executem.

## K

**Keep alive**
Quanta estona es queda el model a la VRAM sense fer res abans de descarregar-se.
Per defecte, 5 minuts. Amb `OLLAMA_KEEP_ALIVE=-1` s'hi queda per sempre: la
primera pregunta ja no triga a arrencar, però la VRAM queda ocupada.

**KV cache**
La memòria on el model guarda els càlculs dels tokens anteriors per no
repetir-los a cada token nou. **Creix amb el context i amb els usuaris
simultanis**, i és la part de la VRAM que la gent oblida de comptar.

## L

**Latència del primer token** *(TTFT, time to first token)*
Quant triga a aparèixer la primera paraula. És el que l'usuari percep com
«ràpid» o «lent», i no té gaire a veure amb els tokens per segon: pot pujar
molt quan hi ha peticions simultànies encara que el cabal total millori.

**llama.cpp**
El motor d'inferència en C++ que hi ha sota d'Ollama. Es pot fer servir
directament: dóna més control i menys comoditat.

**LLM** *(large language model)*
Un model de llenguatge gran: un sistema entrenat per predir el token següent.
Tota la resta —respondre, resumir, programar— surt d'aquesta única capacitat.

**LM Studio**
Aplicació d'escriptori per provar models en local amb interfície gràfica. Bona
per explorar i per a qui no vol terminal; per a un servidor, Ollama.

## M

**MoE** *(mixture of experts)*
Un model dividit en «experts», dels quals només se n'activen uns quants per
token. Un model MoE de 26B pot activar-ne només 4B: va ràpid com un model
petit, **però ocupa la VRAM del gran**, perquè els experts hi han de ser tots.

**Model base vs *instruct***
El **base** només sap continuar text. L'**instruct** ha rebut un entrenament
extra per seguir instruccions i mantenir una conversa. Per a un assistent,
sempre l'instruct.

**Model dens** *(dense)*
El contrari d'un MoE: tots els paràmetres participen en cada token. La majoria
dels models que fem servir al curs són densos.

**Modelfile**
El fitxer on es defineix un model derivat: de quin parteix, quins paràmetres té
i quines instruccions de sistema porta. És l'equivalent d'un `Dockerfile` per a
Ollama. Ho veiem a la C2.

## N

**num_ctx**
La mida de la finestra de context, en tokens. Puja-la i podràs passar-li més
documents; puja-la massa i el model deixa de cabre a la GPU. Compta **0,1–0,2 GB
per cada 1.000 tokens**.

**num_predict**
El sostre de tokens que pot generar en una resposta. Serveix per evitar que un
model s'enrotlli indefinidament.

## O

**Offload**
Quan el model no cap a la VRAM i part de les capes s'executen a la CPU. Funciona,
però l'amplada de banda de la RAM del sistema és deu vegades pitjor: la
diferència és entre 60 tokens/s i 4.

**Ollama**
L'eina que fem servir per executar models en local: baixa el model, el carrega a
la GPU i exposa una API. Fàcil d'instal·lar i **sense cap autenticació**, cosa
que cal tenir present en obrir-la a la xarxa.

**On-premise**
Que s'executa a la infraestructura del client, no en un servei extern. És el
motiu de tot el curs: les dades no surten de l'edifici.

**Open WebUI**
Interfície de xat web per parlar amb Ollama i altres motors. El primer usuari
que s'hi registra es queda d'administrador.

## P

**Paged attention**
La tècnica de vLLM per gestionar la KV cache en blocs, com la memòria virtual
d'un sistema operatiu. Permet atendre moltes peticions sense malgastar memòria.

**Paràmetres**
Els números que el model ha après durant l'entrenament. Es compten en milers de
milions (B): un model «8B» en té uns 8.000 milions. **La quantitat de paràmetres
i els bytes que ocupa cadascun determinen la VRAM que et caldrà.**

**Pesos** *(weights)*
Els valors dels paràmetres. És el que hi ha dins del fitxer del model i el que
s'ha de carregar a la VRAM per poder executar-lo.

**Prefill**
La primera fase de la inferència: llegir tot el que li has passat abans de
generar res. Va limitada pel càlcul, no per la memòria, i és la que marca la
**latència del primer token**.

## Q

**QAT** *(quantization aware training)*
Quantització aplicada ja durant l'entrenament, en comptes de fer-la després. El
model surt preparat per funcionar en pocs bits i perd menys qualitat que si es
quantitza pel seu compte.

**Q3**
Uns 3 bits per pes: **0,4 bytes/paràmetre**. Ocupa poquíssim, però la qualitat
ja se'n ressent de manera visible, sobretot en raonament.

**Q4_K_M**
Quantització a 4 bits, **0,5 bytes/paràmetre** per als càlculs del curs. És **el
punt dolç**: quatre vegades menys memòria que FP16 amb una pèrdua de qualitat
que gairebé no es nota. A la pràctica ocupa una mica més (~0,6), perquè barreja
blocs de 4, 5 i 6 bits.

**Q6**
Uns 6 bits per pes: **0,75 bytes/paràmetre**. Millor qualitat que Q4 i encara
força compacte.

**Q8**
8 bits per pes: **1 byte/paràmetre**. La pèrdua respecte a FP16 és pràcticament
imperceptible, però ocupa el doble que Q4.

**Quantització** *(quantization)*
Guardar els pesos amb menys bits dels que tenien. És el que fa possible executar
en local: un model de 14B en FP16 no cabria en una targeta de 12 GB, i en Q4 sí.

**Quantes capes a la GPU** *(`num_gpu`, GPU layers)*
Quantes capes del model es carreguen a la VRAM. Amb `-1` s'hi posen totes les
que hi càpiguen; la resta cauen a la CPU i fan *offload*.

**Qdrant**
La base de dades vectorial del curs. Desa els embeddings dels fragments amb les
seves metadades i troba els més semblants a una consulta. S'executa en un
contenidor de Docker i porta una consola web a `/dashboard`.

## R

**RAG** *(retrieval-augmented generation)*
Buscar informació als teus documents i passar-li-la al model perquè respongui
amb ella. És la resposta correcta per al 95 % dels casos d'empresa, i no el
*fine-tuning*. Ho veurem a la C4.

**RAG clàssic vs agèntic**
El **clàssic** sempre fa el mateix: cerca, enganxa el que ha trobat i respon.
L'**agèntic** decideix si cerca, on cerca i si li cal tornar-hi. El primer és
previsible; el segon resol preguntes que el primer no pot.

**Reranker**
Un model que reordena els fragments recuperats mirant la pregunta i cada
fragment alhora. És molt més precís que els embeddings i molt més lent, per això
només se li passen els primers candidats. Ho veurem a la C5.

**Recuperació** *(retrieval)*
La part del RAG que busca els fragments rellevants. Si aquí no surt el fragment
bo, el model no el pot fer servir: **la meitat dels problemes d'un RAG són
problemes de recuperació**.

**repeat_penalty**
Penalitza repetir el que ja s'ha dit. Per sobre d'1,2 comença a evitar paraules
que necessita —noms de producte, referències— i la resposta se'n ressent.

**RRF** *(reciprocal rank fusion)*
La manera de fusionar dos rànquings —el dels embeddings i el de BM25— sense
haver de comparar puntuacions que no són comparables entre elles.

## S

**Safetensors**
El format de pesos estàndard a Hugging Face, el que fan servir vLLM i les
llibreries de Python. Els pesos hi van sense quantitzar o quantitzats amb AWQ o
GPTQ. Per a Ollama, el format és GGUF.

**Secure Boot / MOK**
Secure Boot fa que el sistema només carregui mòduls signats, i pot impedir que
carregui el driver de NVIDIA. Es resol desactivant-lo o signant el mòdul amb una
clau pròpia (MOK). Ho vam patir a la C1.

**Solapament** *(overlap)*
Els caràcters que es repeteixen entre dos fragments veïns en partir un document.
Sense solapament, una frase que queda tallada per la meitat no es recupera bé
mai. Al curs fem servir ~100 tokens de solapament sobre fragments de ~800.

**Sortida estructurada** *(structured output)*
Obligar el model a respondre seguint un esquema JSON. No «li demanes» JSON: el
motor només el deixa generar tokens que hi encaixin. Imprescindible si la
resposta ha d'alimentar un altre programa.

## T

**temperature**
Com d'aleatòria és la tria del token següent. 0 fa que sempre respongui igual;
1 el fa creatiu. Per a un assistent d'empresa, **entre 0 i 0,3**: aquí la
creativitat és un defecte.

**Text-to-SQL**
Que el model escrigui la consulta SQL a partir d'una pregunta en llenguatge
natural. Amb dues barreres sempre: validar la consulta abans d'executar-la i
connectar-se amb un usuari de només lectura. Ho veurem a la C6.

**Thinking / raonament**
Alguns models (qwen3, gpt-oss) escriuen el seu raonament abans de la resposta.
Millora els resultats en problemes complexos i **gasta tokens i temps** en els
senzills. A qwen3 es desactiva posant `/no_think` al principi del missatge.

**Token**
La unitat en què el model parteix el text: sol ser un tros de paraula. Tot es
mesura en tokens: el context, la velocitat i, als serveis de pagament, la
factura.

**Tokenitzador** *(tokenizer)*
El que converteix text en tokens. **El català tokenitza pitjor que l'anglès**:
el mateix text ocupa un 25–35 % més de tokens, o sigui més context consumit i
més lentitud.

**Tokens per segon**
La velocitat de generació. És la mesura de rendiment del curs, i es pot estimar
abans de comprar res amb la segona fórmula.

**Tool calling**
Que el model demani executar una funció —consultar una base de dades, cridar una
API— i faci servir el resultat per respondre. És la base dels agents. Ho veurem
a la C5.

**top_k**
Limita la tria als *k* tokens més probables. Amb temperatura baixa gairebé no es
nota.

**top_p** *(nucleus sampling)*
Limita la tria al conjunt de tokens més probables que sumen la probabilitat *p*.
Com el `top_k`, amb temperatura baixa té poc efecte.

## V

**vLLM**
Motor d'inferència pensat per a servidors amb molts usuaris alhora. Amb una sola
petició sol perdre contra Ollama; amb vuit, guanya de llarg gràcies al
*continuous batching* i la *paged attention*.

**VRAM**
La memòria de la targeta gràfica. **És el coll d'ampolla del curs sencer**: si
el model no hi cap, o no s'executa o cau a la CPU i va deu vegades més lent.

---

## Les fórmules del curs

```
VRAM_pesos (GB) ≈ paràmetres (B) × bytes/paràmetre × 1,1

tokens/s ≈ amplada de banda (GB/s) ÷ mida del model (GB)
```

**Bytes per paràmetre:** FP16 = 2 · Q8 = 1 · Q6 = 0,75 · **Q4 = 0,5** · Q3 = 0,4
**Rendiment real:** entre el 60 % i el 80 % del teòric.

Per fer els números sense pensar-hi: [`c1/hardware-calc.xlsx`](../c1/hardware-calc.xlsx).

---

*CIDET · IA en local*
