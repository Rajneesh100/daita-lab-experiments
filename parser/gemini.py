from textwrap import indent
import google.generativeai as genai
import json
import os
from dotenv import load_dotenv

load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))  # Load from parent directory

# Get Gemini API key from environment variable
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is required")

genai.configure(api_key=GEMINI_API_KEY)

def get_gemini_response(pdf_path: str, prompt: str) -> dict:
   
    model = genai.GenerativeModel('models/gemini-2.5-pro')
    # model = genai.GenerativeModel('models/gemini-1.5-pro-latest')


    print(f"pushing file: {pdf_path}...")
    uploaded_file = genai.upload_file(path=pdf_path, display_name="Purchase Order")
    print("File upload done .")

    response = model.generate_content([prompt, uploaded_file])
    print(response)
    try:
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
        print(json.dumps(cleaned_response, indent=2))
        return json.loads(cleaned_response)
    except (json.JSONDecodeError, AttributeError) as e:
        print(f"Error: Failed to parse JSON from the model's response. Details: {e}")
        print("gemini respone:")
        print(response.text)
        print("--------------------------")
        raise ValueError("didn't get valid json from gemini!!")





def extract_pdf_data(pdf_path: str) -> dict:
   
    SCHEMA_INSTRUCTION_PROMPT = """
    You are an expert PDF Purchase Order Parser. Your task is to analyze the provided purchase order PDF and extract structured data from it.
    You must return a single, valid JSON object that adheres to the schema below. Do not include any explanations, markdown formatting, or comments in your output.

    Schema:
    {
    "purchase_order_id": string,
    "order_date": string (Format as YYYY-MM-DD),
    "buyer": { "name": string, "address": string },
    "supplier": { "name": string, "address": string },
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
            "XXS": number, "XS": number, "S": number, "M": number,
            "L": number, "XL": number, "XXL": number, "XXXL": number, "XXXXL": number
        },
        "piece": number, "price": number, "total": number
        }
    ]
    }

    Rules:
    - Dates must be normalized to YYYY-MM-DD format.
    - All numbers must be formatted as numbers, not strings.

    IMPORTANT VISUAL ALIGNMENT RULE:
    - Critically, you must correctly map the quantities to their corresponding size headers (XXS, XS, S, etc.).
    - If a size column in the PDF is empty for a specific line item, its value in the JSON must be 0.
    - Trim whitespace, normalize all colors (e.g., "Blue" and "blue" -> "blue", "Sand Stone" -> "sand stone"), normalize sizes (S, M, L, numeric sizes), parse dates to ISO (YYYY-MM-DD)
    - All numbers (prices, totals, quantities) must be formatted as numbers, not strings.
    - Extract the supplier's address from the "ship to" or equivalent section.
    - For example, if the first number '3' appears under the 'S' column, and the 'XXS' and 'XS' columns are empty, the output must be `"XXS": 0, "XS": 0, "S": 3, ...` and so on. Do not shift the values to the left.
    """

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    return get_gemini_response(pdf_path, SCHEMA_INSTRUCTION_PROMPT)














































if __name__ == "__main__":
    SCHEMA_INSTRUCTION_PROMPT = """
    You are an expert PDF Purchase Order Parser. Your task is to analyze the provided purchase order PDF and extract structured data from it.
    You must return a single, valid JSON object that adheres to the schema below. Do not include any explanations, markdown formatting, or comments in your output.

    Schema:
    {
    "purchase_order_id": string,
    "order_date": string (Format as YYYY-MM-DD),
    "buyer": { "name": string, "address": string },
    "supplier": { "name": string, "address": string },
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
            "XXS": number, "XS": number, "S": number, "M": number,
            "L": number, "XL": number, "XXL": number, "XXXL": number, "XXXXL": number
        },
        "piece": number, "price": number, "total": number
        }
    ]
    }

    Rules:
    - Dates must be normalized to YYYY-MM-DD format.
    - All numbers must be formatted as numbers, not strings.

    IMPORTANT VISUAL ALIGNMENT RULE:
    - Critically, you must correctly map the quantities to their corresponding size headers (XXS, XS, S, etc.).
    - If a size column in the PDF is empty for a specific line item, its value in the JSON must be 0.
    - Dates must be normalized to YYYY-MM-DD format.
    - All numbers (prices, totals, quantities) must be formatted as numbers, not strings.
    - Extract the supplier's address from the "ship to" or equivalent section.
    - For example, if the first number '3' appears under the 'S' column, and the 'XXS' and 'XS' columns are empty, the output must be `"XXS": 0, "XS": 0, "S": 3, ...` and so on. Do not shift the values to the left.
    """


    pdf_file_path = "/Users/rajneesh.kumar/Desktop/llm_games/sample_pdfs/purchase-order.pdf" # Make sure this file is in the same directory
    
    try:
        parsed_data = extract_pdf_data(pdf_file_path)
        print("\n--- Parsed JSON Data ---")
        print(json.dumps(parsed_data, indent=2))
        print("------------------------")
    except (ValueError, FileNotFoundError) as e:
        print(f"An error occurred: {e}")