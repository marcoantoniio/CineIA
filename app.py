import base64
import json
import os
import uuid
from pathlib import Path
from textwrap import dedent

import streamlit as st
from dotenv import load_dotenv

# Load .env file FIRST (Streamlit doesn't do this automatically)
load_dotenv()

from backend.agente_cinedata import create_agente_cinedata_simple


ROOT = Path(__file__).parent
ASSETS = ROOT / "assets"

NODES = [
    {
        "icon": "corner-images/generos.svg",
        "label": "Generos",
        "display": "Gêneros",
        "desc": "Acao · Drama · Comedia · Terror",
        "category": "generos",
    },
    {
        "icon": "corner-images/diretores.svg",
        "label": "Diretores",
        "display": "Diretores",
        "desc": "Elenco · Roteiristas",
        "category": "diretores",
    },
    {
        "icon": "corner-images/bilheteria.svg",
        "label": "Bilheteria",
        "display": "Bilheteria",
        "desc": "Orcamento · Receita · ROI",
        "category": "bilheteria",
    },
    {
        "icon": "corner-images/premiacoes.svg",
        "label": "Premiacoes",
        "display": "Premiações",
        "desc": "Oscar · Indicacoes · Vitorias",
        "category": "premiacoes",
    },
]

DICTIONARY_BY_CATEGORY = {
    "generos": [
        {"field": "generos", "label": "Generos", "type": "text", "note": "Categorias do filme. Pode conter lista ou texto delimitado."},
        {"field": "pais_origem", "label": "Pais de origem", "type": "text", "note": "Pais ou paises associados a producao."},
        {"field": "idiomas", "label": "Idiomas", "type": "text", "note": "Idioma ou idiomas do filme."},
        {"field": "classificacao_mpa", "label": "Classificacao MPA", "type": "text", "note": "Classificacao indicativa, como G, PG, PG-13, R ou Not Rated."},
    ],
    "diretores": [
        {"field": "diretores", "label": "Diretores", "type": "text", "note": "Pode conter lista ou texto delimitado."},
        {"field": "roteiristas", "label": "Roteiristas", "type": "text", "note": "Pode conter lista ou texto delimitado."},
        {"field": "elenco_principal", "label": "Elenco principal", "type": "text", "note": "Principais nomes do elenco."},
        {"field": "produtoras", "label": "Produtoras", "type": "text", "note": "Empresas produtoras do filme."},
    ],
    "bilheteria": [
        {"field": "orcamento", "label": "Orcamento", "type": "numeric(15,2)", "note": "Valor monetario em USD."},
        {"field": "bilheteria_mundial", "label": "Bilheteria mundial", "type": "numeric(15,2)", "note": "Receita global em USD."},
        {"field": "bilheteria_eua_canada", "label": "Bilheteria EUA/Canada", "type": "numeric(15,2)", "note": "Receita em USD nos Estados Unidos e Canada."},
        {"field": "bilheteria_fim_semana_abertura", "label": "Bilheteria de abertura", "type": "numeric(15,2)", "note": "Receita em USD no fim de semana de abertura."},
        {"field": "nota_imdb", "label": "Nota IMDb", "type": "numeric(3,1)", "note": "Nota de 0 a 10."},
        {"field": "votos", "label": "Votos", "type": "integer", "note": "Quantidade de votos no IMDb."},
    ],
    "premiacoes": [
        {"field": "premios_vencidos", "label": "Premios vencidos", "type": "integer", "note": "Quantidade de premios vencidos."},
        {"field": "indicacoes", "label": "Indicacoes", "type": "integer", "note": "Quantidade total de indicacoes."},
        {"field": "indicacoes_oscar", "label": "Indicacoes ao Oscar", "type": "integer", "note": "Quantidade de indicacoes ao Oscar."},
    ],
}

QUICK_QUESTIONS_BY_CATEGORY = {
    "generos": [
        "Quais sao os generos mais frequentes na base?",
        "Qual genero tem a maior nota media no IMDb?",
        "Como a quantidade de filmes por genero mudou ao longo dos anos?",
        "Quais paises aparecem mais em cada genero?",
    ],
    "diretores": [
        "Quais diretores aparecem mais vezes na base?",
        "Quais diretores tem maior nota media no IMDb?",
        "Quais atores aparecem com mais frequencia no elenco principal?",
        "Quais produtoras lancaram mais filmes?",
    ],
    "bilheteria": [
        "Quais filmes tiveram maior bilheteria mundial?",
        "Quais filmes tiveram maior orcamento?",
        "Qual e a relacao entre orcamento e bilheteria mundial?",
        "Quais filmes tiveram maior bilheteria no fim de semana de abertura?",
    ],
    "premiacoes": [
        "Quais filmes tiveram mais premios vencidos?",
        "Quais filmes tiveram mais indicacoes ao Oscar?",
        "Existe relacao entre nota IMDb e premiacoes?",
        "Quais anos concentraram mais indicacoes?",
    ],
}


def file_data_uri(path: Path, mime: str) -> str:
    data = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{data}"


def load_css() -> None:
    st.markdown(f"<style>{(ASSETS / 'style.css').read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def init_state() -> None:
    defaults = {
        "session_id": str(uuid.uuid4()),
        "selected_category": None,
        "messages": [],
        "pending_prompt": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


@st.cache_resource
def get_agent():
    """Initialize agent once per session."""
    return create_agente_cinedata_simple()


def ask_backend(prompt: str) -> tuple[str, str]:
    """Execute prompt using local agent. Returns (answer, sql_query)."""
    try:
        agent = get_agent()
        result = agent.invoke_sync(prompt)
        answer = result.get("output", "Sem resposta.")
        sql_query = result.get("sql_query", "")
        
        return answer, sql_query
    except Exception as exc:
        return f"Erro ao processar: {exc}", ""


def reset_chat() -> None:
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.messages = []
    st.session_state.pending_prompt = None


def render_topbar() -> None:
    logo = file_data_uri(ASSETS / "logo-cropped.png", "image/png")
    st.markdown(
        dedent(f"""
        <div class="brand header-brand">
          <img src="{logo}" alt="Pyar" />
          <div class="brand-title">Cine<span>Data</span></div>
        </div>
        <div class="topbar-line"></div>
        """),
        unsafe_allow_html=True,
    )


def render_reset_action() -> None:
    if st.button("Limpar chat", key="reset-chat", help="Reiniciar conversa"):
        reset_chat()
        st.rerun()


def render_diagram() -> None:
    video = file_data_uri(ASSETS / "pyar-original.mp4", "video/mp4")
    generos_icon = file_data_uri(ASSETS / NODES[0]["icon"], "image/svg+xml")
    diretores_icon = file_data_uri(ASSETS / NODES[1]["icon"], "image/svg+xml")
    bilheteria_icon = file_data_uri(ASSETS / NODES[2]["icon"], "image/svg+xml")
    premiacoes_icon = file_data_uri(ASSETS / NODES[3]["icon"], "image/svg+xml")
    st.markdown(
        f"""
        <style>
          .theme-node {{
            align-items: center;
            background: radial-gradient(circle at 35% 20%, rgba(245, 197, 24, .18), rgba(33, 29, 19, .78));
            border: 1px solid rgba(245, 197, 24, .15);
            border-radius: 50%;
            box-shadow: 0 10px 24px rgba(0, 0, 0, .22), inset 0 1px 0 rgba(255, 255, 255, .05);
            display: flex;
            flex-direction: column;
            justify-content: center;
            height: 170px;
            margin: 0 auto;
            padding: .8rem;
            position: relative;
            z-index: 2;
            text-align: center;
            width: 170px;
          }}
          .theme-node img {{
            background: rgba(245, 197, 24, .12);
            border: 1px solid rgba(245, 197, 24, .2);
            border-radius: 50%;
            height: 54px;
            margin-bottom: .35rem;
            padding: .45rem;
            width: 54px;
          }}
          .theme-node span {{
            color: #aeb5bf;
            display: block;
            font-size: .72rem;
            line-height: 1.35;
          }}
          .hub-wrap {{
            height: 240px;
            margin: 0 auto;
            position: relative;
            width: 100%;
          }}
          .core-pulse {{
            background: radial-gradient(circle, rgba(255, 59, 59, .28) 0%, rgba(255, 59, 59, .14) 34%, rgba(255, 59, 59, 0) 72%);
            border-radius: 50%;
            height: 220px;
            left: 50%;
            pointer-events: none;
            position: absolute;
            top: 50%;
            transform: translate(-50%, -50%) scale(.88);
            width: 220px;
            z-index: 0;
            animation: corePulse 2.8s ease-out infinite;
          }}
          .core-pulse-2 {{
            animation-delay: 1.4s;
          }}
          @keyframes corePulse {{
            0% {{
              opacity: .42;
              transform: translate(-50%, -50%) scale(.88);
            }}
            72% {{
              opacity: .12;
            }}
            100% {{
              opacity: 0;
              transform: translate(-50%, -50%) scale(2.7);
            }}
          }}
          .hub {{
            align-items: center;
            background: radial-gradient(circle, rgba(245, 197, 24, .08), rgba(17, 14, 9, .9));
            border: 2px solid rgba(245, 197, 24, .2);
            border-radius: 50%;
            box-shadow: 0 0 70px rgba(245, 197, 24, .06);
            display: flex;
            height: 220px;
            justify-content: center;
            margin: 0 auto;
            overflow: hidden;
            position: relative;
            z-index: 1;
            width: 220px;
          }}
          .hub video {{
            border-radius: 50%;
            height: 92%;
            object-fit: cover;
            object-position: center center;
            width: 92%;
          }}
          .theme-button-wrap {{
            margin-top: .65rem;
            text-align: center;
          }}
          .theme-desc {{
            color: #aeb5bf;
            display: block;
            font-size: .72rem;
            margin-top: .3rem;
          }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    row_1 = st.columns([1, 1, 1], gap="large")
    with row_1[0]:
        st.markdown(
            f'<div class="theme-node"><img src="{generos_icon}" alt=""><span>{NODES[0]["desc"]}</span></div>',
            unsafe_allow_html=True,
        )
        is_selected = st.session_state.selected_category == NODES[0]["category"]
        if st.button(NODES[0]["display"], key="theme-generos", use_container_width=True, type="primary" if is_selected else "secondary"):
            st.session_state.selected_category = NODES[0]["category"]
    with row_1[1]:
        st.markdown(
            f"""
            <div class="hub-wrap">
              <div class="core-pulse"></div>
              <div class="core-pulse core-pulse-2"></div>
              <div class="hub">
                <video autoplay muted loop playsinline preload="auto">
                  <source src="{video}" type="video/mp4" />
                </video>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with row_1[2]:
        st.markdown(
            f'<div class="theme-node"><img src="{diretores_icon}" alt=""><span>{NODES[1]["desc"]}</span></div>',
            unsafe_allow_html=True,
        )
        is_selected = st.session_state.selected_category == NODES[1]["category"]
        if st.button(NODES[1]["display"], key="theme-diretores", use_container_width=True, type="primary" if is_selected else "secondary"):
            st.session_state.selected_category = NODES[1]["category"]

    row_2 = st.columns([1, 1, 1], gap="large")
    with row_2[0]:
        st.markdown(
            f'<div class="theme-node"><img src="{bilheteria_icon}" alt=""><span>{NODES[2]["desc"]}</span></div>',
            unsafe_allow_html=True,
        )
        is_selected = st.session_state.selected_category == NODES[2]["category"]
        if st.button(NODES[2]["display"], key="theme-bilheteria", use_container_width=True, type="primary" if is_selected else "secondary"):
            st.session_state.selected_category = NODES[2]["category"]
    with row_2[1]:
        st.markdown("<div style='height:1px;'></div>", unsafe_allow_html=True)
    with row_2[2]:
        st.markdown(
            f'<div class="theme-node"><img src="{premiacoes_icon}" alt=""><span>{NODES[3]["desc"]}</span></div>',
            unsafe_allow_html=True,
        )
        is_selected = st.session_state.selected_category == NODES[3]["category"]
        if st.button(NODES[3]["display"], key="theme-premiacoes", use_container_width=True, type="primary" if is_selected else "secondary"):
            st.session_state.selected_category = NODES[3]["category"]

def render_dictionary(category: str) -> None:
    node = next(item for item in NODES if item["category"] == category)
    st.markdown(
        f'<span id="dicionario" class="dict-anchor"></span><div class="theme-title">{node["display"]}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(f'<div class="section-label">Dicionario / {node["display"]}</div>', unsafe_allow_html=True)

    cards = []
    for item in DICTIONARY_BY_CATEGORY[category]:
        cards.append(
            dedent(f"""
            <article class="dict-item">
              <strong>{item["label"]}</strong>
              <code>{item["field"]}</code>
              <p>{item["note"]}</p>
            </article>
            """)
        )

    st.markdown(f'<div class="dict-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def render_quick_questions(category: str) -> None:
    st.markdown('<div class="section-label">Perguntas rapidas</div>', unsafe_allow_html=True)
    for question in QUICK_QUESTIONS_BY_CATEGORY[category]:
        if st.button(question, key=f"q-{category}-{question}"):
            st.session_state.pending_prompt = question


def render_chat() -> None:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            # Display SQL if this message has it
            if message.get("sql_query"):
                with st.expander("📊 Ver SQL executado"):
                    st.code(message["sql_query"], language="sql")

    prompt = st.chat_input("Pergunte sobre filmes, diretores, bilheteria...")
    if prompt:
        st.session_state.pending_prompt = prompt

    if st.session_state.pending_prompt:
        current_prompt = st.session_state.pending_prompt
        st.session_state.pending_prompt = None
        st.session_state.messages.append({"role": "user", "content": current_prompt})

        with st.chat_message("user"):
            st.markdown(current_prompt)

        with st.chat_message("assistant"):
            with st.spinner("Consultando a base de filmes..."):
                answer, sql_query = ask_backend(current_prompt)
            st.markdown(answer)
            
            # Display SQL if available
            if sql_query:
                with st.expander("📊 Ver SQL executado"):
                    st.code(sql_query, language="sql")

        st.session_state.messages.append({
            "role": "assistant", 
            "content": answer,
            "sql_query": sql_query
        })
        st.rerun()


def main() -> None:
    st.set_page_config(page_title="CineData", page_icon="🎬", layout="wide")
    init_state()
    load_css()
    render_reset_action()
    render_topbar()
    render_diagram()

    if st.session_state.selected_category:
        st.markdown('<div class="soft-separator"></div>', unsafe_allow_html=True)
        render_dictionary(st.session_state.selected_category)
        render_quick_questions(st.session_state.selected_category)

    st.markdown('<div class="soft-separator"></div>', unsafe_allow_html=True)
    render_chat()


if __name__ == "__main__":
    main()
