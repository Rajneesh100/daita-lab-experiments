import json
import re

def clean_text(text: str) -> str:
    """Fix common OCR mistakes for size charts and pipes."""
    # Replace mis-OCR 'I' with '|'
    text = re.sub(r'(?<=X)I(?=X)', '|', text)

    # Fix glued pipes next to numbers
    text = re.sub(r'(\d)\|', r'\1 |', text)
    text = re.sub(r'\|(\d)', r'| \1', text)

    # Normalize spaces
    text = re.sub(r'\s{2,}', ' ', text)

    # Handle missing 'L' after M if followed by XL
    text = re.sub(r'\bM\s+(?=XL)', 'M L ', text)

    # Ensure clean pipes (no double pipes, trim spaces)
    text = text.replace("||", "|").strip()

    return text


def recreate_html(json_path, output_html="output.html"):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    html_parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<meta charset='utf-8'/>",
        "<style>",
        "body { margin: 0; background: #f9f9f9; font-family: Arial, sans-serif; }",
        ".page { position: relative; margin: 20px auto; background: white; box-shadow: 0 0 5px rgba(0,0,0,0.2); }",
        ".word { position: absolute; font-size: 12px; white-space: nowrap; }",
        "</style>",
        "</head>",
        "<body>"
    ]

    for page in data["document"]:
        width = page["width"]
        height = page["height"]
        html_parts.append(f"<div class='page' style='width:{width}px; height:{height}px;'>")

        for word in page["words"]:
            x = word["bbox"]["x"]
            y = word["bbox"]["y"]
            w = word["bbox"]["w"]
            h = word["bbox"]["h"]

            text = clean_text(word["text"])
            # escape HTML-sensitive chars
            text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

            html_parts.append(
                f"<span class='word' style='left:{x}px; top:{y}px; width:{w}px; height:{h}px;'>{text}</span>"
            )

        html_parts.append("</div>")

    html_parts.append("</body></html>")

    with open(output_html, "w", encoding="utf-8") as f:
        f.write("\n".join(html_parts))

    print(f"Recreated layout saved to {output_html}")


if __name__ == "__main__":
    recreate_html("output.json", "output.html")
