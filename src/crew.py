"""Crew XAU AI PRO (compatible con el scaffold estándar CrewAI).

Este módulo existe para cumplir el contrato de estructura esperado por
validadores/plataformas de deploy que buscan ``src/crew.py`` +
``src/config/`` (patrón CrewAI: pyproject.toml + poetry.lock/uv.lock).

El crew aquí definido es una demostración mínima: NO realiza operaciones
de trading ni llama a APIs externas por sí mismo. El comportamiento real
del proyecto XAU AI PRO vive en ``app/`` y ``Python/``.
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
    """Crew mínimo en el patrón esperado por los templates CrewAI."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def analyst(self):
        """Define al agente 'analyst' (config en src/config/agents.yaml)."""
        return Agent(config=self.agents_config["analyst"], verbose=True)

    @task
    def market_brief(self):
        """Define la tarea 'market_brief' (config en src/config/tasks.yaml)."""
        return Task(config=self.tasks_config["market_brief"])

    @crew
    def crew_exec(self):
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
    XauAiProCrew().crew_exec().kickoff()


if __name__ == "__main__":
    run()