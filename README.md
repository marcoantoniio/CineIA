# CineData Streamlit

Versao Streamlit do frontend CineData.

## Executar

```bash
pip install -r requirements.txt
streamlit run app.py --server.port 8501
```

Acesse:

```text
http://localhost:8501
```

## Backend

Por padrao, o chat tenta conectar em:

```text
ws://localhost:8000/ws/{session_id}
```

Para trocar o endereco:

```bash
set CINEDATA_WS_URL=ws://localhost:8000/ws/{session_id}
```

## Estrutura

```text
app.py                    App Streamlit
requirements.txt          Dependencias
assets/style.css          Estilos
assets/logo-cropped.png   Logo
assets/pyar-original.mp4  Video central
assets/corner-images/     Icones dos quatro temas
```
