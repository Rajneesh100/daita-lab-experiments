import easyocr
import json
import numpy as np
from pdf2image import convert_from_path

def pdf_to_easyocr_json(pdf_path, output_json="easy_ocr_output.json"):
    reader = easyocr.Reader(["en"])  # load once
    pages = convert_from_path(pdf_path, dpi=300)

    all_pages = []
    for page_num, page in enumerate(pages, start=1):
        # Convert PIL.Image -> numpy array
        img = np.array(page)

        results = reader.readtext(img)

        words = []
        for i, (bbox, text, conf) in enumerate(results):
            # bbox is [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
            x = int(min([p[0] for p in bbox]))
            y = int(min([p[1] for p in bbox]))
            w = int(max([p[0] for p in bbox]) - x)
            h = int(max([p[1] for p in bbox]) - y)

            words.append({
                "id": i,
                "text": text,
                "bbox": { "x": x, "y": y, "w": w, "h": h },
                "confidence": float(conf)
            })

        page_json = {
            "page": page_num,
            "width": page.width,
            "height": page.height,
            "words": words
        }
        all_pages.append(page_json)

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump({"document": all_pages}, f, ensure_ascii=False, indent=2)

    print(f"OCR results saved to {output_json}")


if __name__ == "__main__":
    pdf_path = "/Users/rajneesh.kumar/Desktop/llm_games/ocr/sample_pdfs/purchase-order_8.pdf"   # put your PDF here
    pdf_to_easyocr_json(pdf_path, "easy_ocr_output.json")
