# Exemples d'API

Quatre maneres de parlar amb el model des de codi. Totes fan servir
`assistent-valles`, el model que es crea a partir del [`Modelfile`](../Modelfile).

```bash
ollama create assistent-valles -f ../Modelfile   # si encara no el tens
pip install openai ollama                        # jq per al de curl
```

| Fitxer | Què ensenya |
|---|---|
| [`curl-chat.sh`](curl-chat.sh) | L'API crua, amb i sense streaming |
| [`openai_client.py`](openai_client.py) | El mateix codi que faries servir amb OpenAI |
| [`ollama_client.py`](ollama_client.py) | La llibreria oficial, amb el que només fa Ollama |
| [`structured_output.py`](structured_output.py) | JSON garantit per esquema |

```bash
./curl-chat.sh
python openai_client.py
python ollama_client.py
python structured_output.py
```

---

*CIDET · IA en local · Classe 2*
