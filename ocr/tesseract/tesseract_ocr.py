
import pytesseract
from pytesseract import Output
from pdf2image import convert_from_path
import json
import os

def pdf_to_ocr_json(pdf_path, output_json="output.json", dpi=300):
    # Convert PDF pages to images
    pages = convert_from_path(pdf_path, dpi=dpi)

    all_pages = []

    for page_num, page in enumerate(pages, start=1):
        # Convert page to text with bounding boxes
        data = pytesseract.image_to_data(page, output_type=Output.DICT)

        words = []
        for i in range(len(data["text"])):
            if data["text"][i].strip() != "":  # only non-empty
                word = {
                    "id": i,
                    "text": data["text"][i],
                    "bbox": {
                        "x": data["left"][i],
                        "y": data["top"][i],
                        "w": data["width"][i],
                        "h": data["height"][i]
                    },
                    "confidence": data["conf"][i],
                    "line_id": data["line_num"][i],
                    "block_id": data["block_num"][i],
                    "par_id": data["par_num"][i]
                }
                words.append(word)

        page_json = {
            "page": page_num,
            "width": page.width,
            "height": page.height,
            "words": words
        }

        all_pages.append(page_json)

    # Save to JSON file
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump({"document": all_pages}, f, ensure_ascii=False, indent=2)

    print(f"OCR results saved to {output_json}")


if __name__ == "__main__":
    # Example usage
    pdf_path = "/Users/rajneesh.kumar/Desktop/llm_games/ocr/sample_pdfs/purchase-order_8.pdf"   # put your PDF here
    pdf_to_ocr_json(pdf_path, "output.json")
