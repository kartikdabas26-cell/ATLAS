from fastapi import APIRouter, HTTPException

from app.explanation.builder import build_explanation
from app.models.scenario import ScenarioRequest
from app.simulation.engine import run_simulation


router = APIRouter(
    prefix="/api",
    tags=["explanations"],
)


@router.post("/scenario/explain")
def explain_scenario(
    scenario: ScenarioRequest,
):
    """
    Run the deterministic ATLAS simulation and generate
    a structured, traceable explanation from its results.
    """

    try:

        simulation = run_simulation(
            scenario
        )

        explanation = build_explanation(
            simulation
        )

        return {
            "simulation": simulation,
            "explanation": explanation,
        }

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "ATLAS explanation generation failed: "
                f"{exc}"
            ),
        ) from exc