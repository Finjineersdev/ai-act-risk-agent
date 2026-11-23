"""Assess the page's example descriptions once with the full model and save them for the demo.

set -a; . ./.env; set +a; uv run python scripts/save_examples.py      # calls Claude
"""

import json
from datetime import date

import anthropic
from actrag.api import CORPUS_DATE, DISCLAIMER
from actrag.demo import FULL_MODEL
from actrag.retrieve import Retriever

from riskagent.agent import assess
from riskagent.api import STATIC

DESCRIPTIONS = [
    "We sell software that screens CVs and ranks job applicants for interviews.",
    "A chatbot on our website answers customer questions about orders and returns.",
    "An email spam filter that sorts incoming messages for our staff.",
]


def main() -> None:
    retriever, client, out = Retriever.load(), anthropic.Anthropic(), []
    for d in DESCRIPTIONS:
        o = assess(d, [], retriever, client, model=FULL_MODEL)
        assert o.status == "assessed", (d, o.status, o.checked and o.checked.problems)
        out.append(
            {
                "description": d,
                "saved_on": date.today().isoformat(),
                "status": o.status,
                "assessment": o.assessment,
                "problems": o.checked.problems,
                "model": FULL_MODEL,
                "corpus_date": CORPUS_DATE,
                "disclaimer": DISCLAIMER,
            }
        )
        print(f"{d[:40]}…: {o.assessment['tier']}", flush=True)
    (STATIC / "examples.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
