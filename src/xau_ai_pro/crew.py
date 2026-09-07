"""Crew XAU AI PRO (variante con nombre de paquete, src/xau_ai_pro/crew.py).

Espejo de src/crew.py para el layout estándar CrewAI
(``src/<paquete>/crew.py`` + ``src/<paquete>/config/``), por si el
validador deriva el path a partir del nombre del proyecto en pyproject.toml
(xau-ai-pro -> xau_ai_pro).

Crew de demostración mínima: NO realiza operaciones de trading ni llama a
APIs externas por sí mismo. El comportamiento real vive en ``app/`` y
``Python/``.
"""

from __future__ import annotations

try:  # pragma: no cover
    from crewai import Agent, Crew, Process, Task
    from crewai.project import CrewBase, agent, crew, task

    CREWAI_AVAILABLE = True
except ImportError:  # pragma: no cover
    CREWAI_AVAILABLE = False
    Agent = Task = object
    Process = None
    Crew = None
    CrewBase = lambda cls: cls
    agent = lambda method: method
    task = lambda method: method
    crew = lambda method: method


@CrewBase
class XauAiProCrew:
    """Crew mínimo en el patrón estándar CrewAI (package layout)."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def analyst(self):
        """Define al agente 'analyst' (config en src/xau_ai_pro/config/agents.yaml)."""
        return Agent(config=self.agents_config["analyst"], verbose=True)

    @task
    def market_brief(self):
        """Define la tarea 'market_brief' (config en src/xau_ai_pro/config/tasks.yaml)."""
        return Task(config=self.tasks_config["market_brief"])

    @crew
    def crew(self):
        """Devuelve el Crew listo para kickoff (requiere crewai instalado)."""
        if not CREWAI_AVAILABLE:
            raise RuntimeError(
                "crewai no está instalado. Revisa pyproject.toml / poetry.lock."
            )
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )


def run() -> None:
    """Punto de entrada básico (opcional) para validación/manual."""

    if not CREWAI_AVAILABLE:
        print(
            "AVISO: crewai no está instalado; solo se valida la estructura. "
            "Instala dependencias con 'pip install -e .' para ejecutar el crew."
        )
        return
    XauAiProCrew().crew().kickoff()


if __name__ == "__main__":
    run()