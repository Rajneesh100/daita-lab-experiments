import json
import fitz  # PyMuPDF
from PIL import Image
import io
import tempfile
import os
from phi.agent import Agent
from phi.model.ollama import Ollama

ollama_model = "llama3.2-vision:11b"
ollama_url = "http://localhost:11434"

SCHEMA_INSTRUCTION = """
You are a PDF Purchase Order Parser. Your ONLY job is to output a JSON object.
- Output must be valid JSON and nothing else.
- Do not use markdown, bullets, or notes.
- Follow the exact schema below.

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
  "net_order_value": number,
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
      "total": number
    }
  ]
}

Rules:
- All sizes must be present, missing values = 0.
- Dates must be normalized to YYYY-MM-DD.
- Numbers must be plain numbers (not strings).
- Only valid JSON output, no extra text.
- Fecting count of different sizes look just vertically below position if a int value is present then that's it count and if it's empty that means that value is zero
"""

SCHEMA_INSTRUCTION_PROMPT = """
    You are an expert PDF Purchase Order Parser. Your task is to analyze the provided purchase order PDF and extract structured data from it.
    You must return a single, valid JSON object that adheres to the schema below. Do not include any explanations, markdown formatting, or comments in your output.

    Schema:
    {
      "purchase_order_id": string,
      "order_date": string (Format as YYYY-MM-DD),
      "buyer": {
        "name": string,
        "address": string
      },
      "supplier": {
        "name": string,
        "address": string
      },
      "currency": string (infer from symbols like $ or state explicitly if mentioned),
      "total_quantity": number,
      "net_order_value": number,
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
          "total": number
        }
      ]
    }

    Rules:
    - Critically, you must correctly map the quantities to their corresponding size headers (XXS, XS, S, etc.).
    - If a size column in the PDF is empty for a specific line item, its value in the JSON must be 0.
    - Dates must be normalized to YYYY-MM-DD format.
    - All numbers (prices, totals, quantities) must be formatted as numbers, not strings.
    - If a size column is visually empty, its value must be 0.
    - For example, if the first number '3' appears under the 'S' column, and the 'XXS' and 'XS' columns are empty, the output must be `"XXS": 0, "XS": 0, "S": 3, ...` and so on. Do not shift the values to the left.
    - Extract the supplier's address from the "ship to" or equivalent section.
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

def pdf_to_images(pdf_path: str):
    """Render each page of PDF to PNG images using PyMuPDF."""
    doc = fitz.open(pdf_path)
    images = []
    for page in doc:
        pix = page.get_pixmap(dpi=200)
        img_bytes = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_bytes))
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            img.save(tmp.name, "PNG")
            images.append(tmp.name)
    return images

def safe_json_parse(raw: str) -> dict:
    """Extract JSON object from raw model response."""
    import re
    match = re.search(r"\{[\s\S]*\}", raw)
    if not match:
        raise ValueError(f"No JSON object found in response:\n{raw}")
    return json.loads(match.group(0))

def parse_pdf_with_images(pdf_path: str) -> dict:
    image_paths = pdf_to_images(pdf_path)
    results = []

    for idx, img_path in enumerate(image_paths, 1):
        response = parser_agent.run(
            f"Extract purchase order details from page {idx}. Output ONLY valid JSON.",
            images=[img_path]
        )
        results.append(response.content.strip())
        os.unlink(img_path)  # cleanup temp file

    # If multi-page, you could merge line_items across results
    return safe_json_parse(results[0])

if __name__ == "__main__":
    pdf_file = "/Users/rajneesh.kumar/Desktop/llm_games/sample_pdfs/purchase-order.pdf"
    parsed_data = parse_pdf_with_images(pdf_file)
    print(json.dumps(parsed_data, indent=2))
