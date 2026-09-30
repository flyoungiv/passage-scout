SAMPLE = """# Why cities plant trees

Urban trees provide shade and cool the air through **evapotranspiration**: water moves from soil through a tree and evaporates from leaves.

## Two kinds of cooling

- Shade reduces the solar energy reaching streets and buildings.
- Evapotranspiration uses heat to turn liquid water into water vapor.

Trees also intercept rainfall, offer habitat, and make streets more pleasant. Their benefits depend on *species, water availability, placement, and care*.

## A question worth investigating

Planting a tree is only the beginning. Young trees need maintenance, and dry conditions can limit cooling. A good urban forestry plan matches species and location to local conditions.

This short sample was written for Passage Scout. Its prepared evidence points to public EPA guidance; it is not a live web search.
"""
QUESTIONS = [
    "How do trees cool cities?",
    "What affects how much cooling a tree provides?",
]
EVIDENCE = [
    {
        "id": 1,
        "title": "EPA: Benefits of Trees and Vegetation",
        "url": "https://www.epa.gov/heatislands/benefits-trees-and-vegetation",
        "passage": "Prepared paraphrase: Trees cool surroundings through shade and evapotranspiration; placement and plant characteristics influence their benefits.",
        "score": 1.0,
    }
]


def answer(question: str, document: str) -> dict:
    if document == SAMPLE and question in QUESTIONS:
        body = (
            "Trees cool cities through shade, which blocks incoming solar energy, and "
            "evapotranspiration, which uses heat as water evaporates from leaves. [1]"
        )
        if question == QUESTIONS[1]:
            body = (
                "Cooling depends on tree characteristics and placement. Water availability "
                "and ongoing care also matter, as the sample explains. EPA guidance describes "
                "shade and evapotranspiration as the two cooling mechanisms. [1]"
            )
        return {
            "mode": "demo",
            "label": "Prepared demo • no external calls",
            "answer": body,
            "citations": EVIDENCE,
        }
    return {
        "mode": "demo",
        "label": "Illustrative demo • not document-grounded",
        "answer": "This is an illustrative response showing where an answer would appear. "
        "I have not analyzed or verified this document. Switch to Live RAG to search "
        "the web and generate an evidence-backed answer, or use a prepared sample question.",
        "citations": [],
    }
