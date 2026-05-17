"""
Agente CineData — movies data analyst (simplified for Streamlit)
"""

import time
import hashlib
import asyncio
from typing import Any, Dict, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_community.utilities import SQLDatabase

from backend.postgres_cinedata import PostgresCinedataConnector
from backend.llm_provider import get_llm
from backend.cinedata_prompts import CINEDATA_ROUTER_PROMPT, CINEDATA_PREFIX, CINEDATA_EXAMPLES


RESPONSE_FORMATTER_PROMPT = """
Você é um assistente especializado em análise de dados de filmes. 
Sua tarefa é transformar dados brutos de uma query SQL em uma resposta elegante, clara e informativa em português.

Dados brutos da query:
{raw_data}

Pergunta original do usuário:
{question}

Escreva uma resposta natural e bem formatada que:
1. Responda diretamente à pergunta do usuário
2. Apresente os dados de forma clara e elegante
3. Use formatação com * para destaque quando apropriado
4. Adicione contexto e interpretação quando relevante
5. Seja conciso mas informativo
6. Use números em formato PT-BR (ex: 1.234,56 em vez de 1234.56)

Resposta formatada:
"""


class AgenteCinedataSimple:
    """Simple movie data analyst agent for Streamlit (no LangGraph, direct SQL execution)."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self._response_cache: Dict[str, Dict] = {}
        self._cache_max = 200

        print("🎬 [Agente CineData] Inicializando...")

        self.db = PostgresCinedataConnector.get_database()
        self.llm_fast = get_llm(role="fast", temperature=0.0, max_tokens=2048)
        self.llm_primary = get_llm(
            role="primary", temperature=0.0, max_tokens=4096,
            stop_sequences=["\nObservation"],
        )
        self.llm_formatter = get_llm(role="primary", temperature=0.7, max_tokens=1024)

        router_template = ChatPromptTemplate.from_messages([
            ("system", CINEDATA_ROUTER_PROMPT),
            ("user", "{input}")
        ])
        self.parser = JsonOutputParser()
        self.router_chain = router_template | self.llm_fast | self.parser

        print("✅ [Agente CineData] Pronta!")

    def _extract_sql_and_result(self, agent_output: str) -> tuple[str, str]:
        """Extract SQL query and final answer from agent output."""
        sql_query = None
        final_answer = agent_output

        if "SELECT" in agent_output:
            lines = agent_output.split("\n")
            sql_lines = []
            capture = False
            for line in lines:
                if "SELECT" in line:
                    capture = True
                if capture:
                    sql_lines.append(line)
                    if ";" in line:
                        break
            if sql_lines:
                sql_query = "\n".join(sql_lines).strip()

        return sql_query, final_answer

    def _route_question(self, user_input: str) -> Optional[Dict]:
        """Route question: greetings or filmes."""
        try:
            raw = self.router_chain.invoke({"input": user_input})
            category = raw.get("category", "filmes")
            if category == "greetings":
                return {"category": "greetings", "output": "Olá! Sou o Agente CineData, especializado em análise de dados de filmes. Como posso ajudar?"}
            return {"category": category}
        except Exception as e:
            print(f"[Router Error] {e}")
            # Fallback: assume it's about movies
            return {"category": "filmes"}

    def _format_response(self, raw_data: str, question: str) -> str:
        """Use LLM to format raw SQL results into a nice response."""
        try:
            prompt = RESPONSE_FORMATTER_PROMPT.format(
                raw_data=raw_data,
                question=question
            )
            response = self.llm_formatter.invoke(prompt)
            return response.content
        except Exception as e:
            print(f"[Formatter Error] {e}")
            return raw_data

    def _execute_sql_agent(self, user_input: str) -> Dict[str, Any]:
        """Execute simple SQL agent (invoke synchronously)."""
        prompt_text = f"""{CINEDATA_PREFIX}

<tools>
1. sql_db_query: Execute a PostgreSQL SQL query on db_filmes.filmes
2. final_answer: Provide the final plain-text answer (tables allowed)
</tools>

Use the following format:
Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [sql_db_query, final_answer]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final response in plain text (tables allowed).

<examples>
{CINEDATA_EXAMPLES}
</examples>

Question: {user_input}
Thought:"""

        try:
            response = self.llm_primary.invoke(prompt_text)
            output = response.content
            sql_query, final_answer = self._extract_sql_and_result(output)

            # Try to execute SQL if found
            if sql_query and "SELECT" in sql_query:
                try:
                    raw_result = self.db.run(sql_query)
                    # Format the response with Claude
                    final_answer = self._format_response(raw_result, user_input)
                except Exception as e:
                    final_answer = f"Query result: {raw_result if raw_result else 'No data found'}"
            else:
                # No SQL found, format what we have
                final_answer = self._format_response(final_answer, user_input)

            return {
                "output": final_answer,
                "sql_query": sql_query,
                "category": "filmes",
            }
        except Exception as e:
            print(f"[SQL Agent Error] {e}")
            return {
                "output": f"Erro ao processar: {str(e)}",
                "sql_query": None,
                "category": "error",
            }

    def invoke_sync(self, user_input: str) -> Dict[str, Any]:
        """Synchronous invoke (for Streamlit)."""
        start = time.time()

        # Check cache
        cache_key = hashlib.md5(user_input.strip().lower().encode()).hexdigest()
        if cache_key in self._response_cache:
            cached = self._response_cache[cache_key]
            return cached

        # Route
        route_result = self._route_question(user_input)
        if route_result and route_result.get("category") == "greetings":
            result = {
                "output": route_result.get("output", "Olá! Como posso ajudar com dados de filmes?"),
                "sql_query": None,
                "category": "greetings",
            }
        else:
            result = self._execute_sql_agent(user_input)

        result["timing"] = {"total": time.time() - start}

        # Cache
        if result.get("output"):
            if len(self._response_cache) >= self._cache_max:
                del self._response_cache[next(iter(self._response_cache))]
            self._response_cache[cache_key] = result

        return result


def create_agente_cinedata_simple() -> AgenteCinedataSimple:
    return AgenteCinedataSimple()

