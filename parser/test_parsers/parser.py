import json
from phi.agent import Agent
from phi.model.ollama import Ollama
from PyPDF2 import PdfReader

ollama_model = "llama3.2-vision:11b"
ollama_url = "http://localhost:11434"

SCHEMA_INSTRUCTION = """
You are a PDF Purchase Order Parser. Your job is to extract structured data from purchase order PDFs.
Always return a single valid JSON object in the defined schema. No explanations, no markdown, no comments.

Schema:
{
  "purchase_order_id": string,
  "order_date": string (YYYY-MM-DD),
  "buyer": {
    "name": string,
    "address": string
  },
  "supplier": {
    "name": string,
    "address": string
  },
  "currency": string,
  "total_quantity": number,
  "net_order_value": number
  "total_amount": number,
  "line_items": [
    {
      "model_id": string,
      "description": string,
      "article": string,
      "color": string,
      "sizes": {
        "XXS": number,
        "XS": number,
        "S": number,
        "M": number,
        "L": number,
        "XL": number,
        "XXL": number,
        "XXXL": number,
        "XXXXL": number
      },
      "piece": number,
      "price": number,
      "total": number,
    }
  ]
}

Rules:
- All sizes (XXS, XS, S, M, L, XL, XXL, XXXL, XXXXL) must be present for every line item.
- If a size has no quantity in the PDF, output 0.
- Dates must be normalized to YYYY-MM-DD.
- Numbers must be plain numbers (not strings).
"""

ollama_chat = Ollama(
    id=ollama_model,
    base_url=ollama_url,
)

parser_agent = Agent(
    name="PDFParser",
    role=SCHEMA_INSTRUCTION,
    model=ollama_chat,
    show_tool_calls=True,
    markdown=False,
)

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract raw text from a PDF file."""
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text.strip()

def parse_pdf(pdf_path: str) -> dict:
    """Parses a purchase order PDF and returns structured JSON."""
    raw_text = extract_text_from_pdf(pdf_path)
    response = parser_agent.run(
        f"Extract purchase order details from the following text:\n\n{raw_text}"
    )
    try:
        return json.loads(response.content.strip())
    except Exception as e:
        raise ValueError(f"Failed to parse JSON: {e}\nRaw response: {response.content}")

if __name__ == "__main__":
    pdf_file = "/Users/rajneesh.kumar/Desktop/llm_games/sample_pdfs/purchase-order.pdf"
    parsed_data = parse_pdf(pdf_file)
    print(json.dumps(parsed_data, indent=2))