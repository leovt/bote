#!/usr/bin/env python3
"""Interactive helper for generating missing BOTE card art."""

import argparse
import base64
import datetime as dt
import os
import random
import re
import shutil
import subprocess
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent
CARDS_FILE = ROOT / "cards.yaml"
CLIENT_DIR = ROOT / "client"
PREVIEW_DIR = ROOT / "art_previews"
DEFAULT_MODEL = "gpt-image-1.5"
DEFAULT_PROMPT_MODEL = "gpt-5-mini"
DEFAULT_PROMPT_MAX_OUTPUT_TOKENS = 800
DEFAULT_SIZE = "1536x1024"
DEFAULT_QUALITY = "auto"
FINAL_IMAGE_INSTRUCTIONS = (
    "Horizontal 3:2 composition, strong readable silhouette, dramatic lighting, rich environment. "
    "No text, no logos, no card border, no watermark, no UI elements."
)
STYLE_VARIANTS = {
    "red": [
        "basalt cliffs, black rock, volcanic glass, smoke, and a restrained ember glow",
        "a rugged mountain pass with red banners, iron weapons, dust, and stormy skies",
        "a fortress courtyard or ruined castle built from dark stone, lit by torches",
        "an ash-covered battlefield with broken masonry, bronze armor, and distant heat haze",
        "a canyon of rust-colored stone, windblown sand, and harsh sunset light",
        "a forge-city or mine entrance with iron chains, rock walls, and muted coals",
        "a highland war camp among crags, leather, steel, and overcast light",
        "ancient red-stone ruins with carved pillars, dry grass, and dramatic shadows",
    ],
    "green": [
        "deep woodland with mossy stones, roots, filtered light, and natural greens",
        "misty hills, old trees, wet earth, and a cool dawn atmosphere",
        "overgrown ruins reclaimed by vines, ferns, and dappled sunlight",
        "wild meadow at the forest edge with rocks, clouds, and restless wind",
        "ancient grove with massive trunks, mushrooms, lichen, and muted earth tones",
    ],
    "source": [
        "a primal landscape vista with dramatic natural forces and atmospheric depth",
        "an ancient shrine integrated into the landscape, quiet but powerful",
        "a wide cinematic environment with elemental energy implied through light and weather",
    ],
    "neutral": [
        "weathered stone architecture, worn banners, and moody natural light",
        "a windswept landscape with ruins, cliffs, and a grounded fantasy tone",
        "a dramatic but believable environment with varied materials and restrained color",
    ],
}
MEDIUM_VARIANTS = [
    "oil-painting inspired digital art with textured brushwork",
    "ink-and-wash fantasy illustration with selective color",
    "classic adventure-book cover painting with cinematic depth",
    "semi-realistic concept art with crisp silhouettes and painterly detail",
    "gouache-like fantasy illustration with matte colors and strong shapes",
]


def load_dotenv(path=ROOT / ".env"):
    if not path.exists():
        return
    for line in path.read_text(encoding="utf8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        os.environ.setdefault(key, value)


def load_cards():
    with CARDS_FILE.open(encoding="utf8") as stream:
        return yaml.safe_load(stream)


def english_name(card):
    names = card.get("names", {})
    return names.get("en") or next(iter(names.values()), "<unnamed>")


def existing_image_path(art):
    image = art.get("image")
    if not image:
        return None
    return CLIENT_DIR / image


def iter_art_cards(data):
    for card_id, card in data["cards"].items():
        for art_id, art in card.get("art", {}).items():
            yield int(card_id), card, int(art_id), art


def missing_art_cards(data):
    for card_id, card, art_id, art in iter_art_cards(data):
        image_path = existing_image_path(art)
        if image_path is None or not image_path.exists():
            yield card_id, card, art_id, art


def describe_card(card):
    bits = [card["type"]]
    if card.get("subtypes"):
        bits.append(" ".join(card["subtypes"]))
    if "strength" in card and "toughness" in card:
        bits.append(f"{card['strength']}/{card['toughness']}")
    if card.get("cost"):
        bits.append(f"cost {card['cost']}")
    return ", ".join(bits)


def card_rules(card):
    rules = []
    if card.get("effect"):
        rules.append(card["effect"])
    rules.extend(card.get("effects", []))
    for ability in card.get("abilities", []):
        if "keyword" in ability:
            rules.append(ability["keyword"])
        elif "effect" in ability:
            cost = ability.get("cost")
            rules.append(f"{cost}: {ability['effect']}" if cost else ability["effect"])
    return "; ".join(rules)


def final_image_prompt(prompt):
    return f"{prompt.rstrip(' .')}. {FINAL_IMAGE_INSTRUCTIONS}"


def require_openai_client():
    load_dotenv()
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise SystemExit(
            "The openai package is not installed. Run `pip install -r requirements.txt` first."
        ) from exc
    return OpenAI()


def response_text(response):
    if getattr(response, "output_text", None):
        return response.output_text.strip()

    parts = []
    if hasattr(response, "model_dump"):
        response = response.model_dump()

    if isinstance(response, dict):
        output = response.get("output", [])
    else:
        output = getattr(response, "output", [])

    for item in output:
        if isinstance(item, dict):
            content_items = item.get("content", [])
        else:
            content_items = getattr(item, "content", [])
        for content in content_items:
            if isinstance(content, dict):
                text = content.get("text")
            else:
                text = getattr(content, "text", None)
            if text:
                parts.append(text)
    return " ".join(parts).strip()


def response_summary(response):
    if hasattr(response, "model_dump"):
        response = response.model_dump()
    if not isinstance(response, dict):
        return f"type={type(response).__name__}"

    summary = []
    for key in ("id", "status", "model"):
        if response.get(key):
            summary.append(f"{key}={response[key]}")
    incomplete = response.get("incomplete_details")
    if incomplete:
        summary.append(f"incomplete_details={incomplete}")
    error = response.get("error")
    if error:
        summary.append(f"error={error}")
    output_types = [
        item.get("type")
        for item in response.get("output", [])
        if isinstance(item, dict) and item.get("type")
    ]
    if output_types:
        summary.append(f"output_types={output_types}")
    return ", ".join(summary) or "empty response"


def prompt_brief(card, art):
    name = english_name(card)
    flavour = art.get("flavour", {}).get("en", "")
    rules = card_rules(card)
    details = [f"Card name: {name}", f"Card details: {describe_card(card)}"]
    if rules:
        details.append(f"Abilities and rules: {rules}")
    if flavour:
        details.append(f"Flavor: {flavour}")
    return "\n".join(details)


def propose_gpt_prompt(card, art, prompt_model, prompt_max_output_tokens):
    client = require_openai_client()
    optional_keys = set()
    request = {
        "model": prompt_model,
        "instructions": (
            "Write one concise image-generation prompt for original fantasy card game artwork. "
            "Use the card name, creature/type details, abilities, rules, and flavor as inspiration. "
            "Do not use any existing character, franchise, artist name, logo, or copyrighted setting. "
            "Do not include text rendering instructions or aspect-ratio instructions. "
            "Do not assume a fixed visual style; propose a distinctive style and scene that fit this card. "
            "Return only the image prompt, one paragraph."
        ),
        "input": prompt_brief(card, art),
        "max_output_tokens": prompt_max_output_tokens,
    }
    if prompt_model.startswith("gpt-5"):
        request["reasoning"] = {"effort": "minimal"}
        request["text"] = {"verbosity": "low"}
        optional_keys.update({"reasoning", "text"})

    try:
        response = client.responses.create(**request)
    except Exception as exc:
        message = str(exc).lower()
        is_optional_param_error = (
            optional_keys
            and any(key in message for key in optional_keys)
            and any(marker in message for marker in ("unknown", "unsupported", "unexpected"))
        )
        if not isinstance(exc, TypeError) and not is_optional_param_error:
            raise
        for key in optional_keys:
            request.pop(key, None)
        response = client.responses.create(**request)
    prompt = response_text(response)
    if not prompt:
        raise SystemExit(
            "The prompt-generation API response did not contain text. "
            f"Response summary: {response_summary(response)}"
        )
    return final_image_prompt(prompt)


def propose_local_prompt(card, art):
    name = english_name(card)
    frame = art.get("frame") or card.get("color") or "neutral"
    frame_styles = STYLE_VARIANTS.get(frame, STYLE_VARIANTS["neutral"])
    style = random.choice(frame_styles)
    medium = random.choice(MEDIUM_VARIANTS)
    flavour = art.get("flavour", {}).get("en", "")
    rules = card_rules(card)

    details = [f"Card name: {name}.", f"Card details: {describe_card(card)}."]
    if rules:
        details.append(f"Game mechanics to interpret visually: {rules}.")
    if flavour:
        details.append(f"Flavor mood: {flavour}")

    prompt = " ".join([
        f"Create original fantasy trading-card artwork, {medium}.",
        *details,
        f"Art direction: {style}.",
        f"Let the {frame} frame color inform accents only; avoid an all-{frame}, all-fire, or monochrome image.",
    ])
    return final_image_prompt(prompt)


def propose_prompts(card, art, prompt_model, prompt_max_output_tokens, local_count=2):
    print(f"Generating one prompt with {prompt_model}...")
    prompts = [propose_gpt_prompt(card, art, prompt_model, prompt_max_output_tokens)]
    seen = set(prompts)
    while len(prompts) < local_count + 1:
        prompt = propose_local_prompt(card, art)
        if prompt in seen:
            continue
        prompts.append(prompt)
        seen.add(prompt)
    random.shuffle(prompts)
    return prompts


def slugify(value):
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = value.strip("_")
    return value or "card"


def print_missing(items):
    if not items:
        print("No cards without images found.")
        return
    print("Cards without images:")
    for card_id, card, art_id, art in items:
        reason = "empty image" if not art.get("image") else f"missing file: client/{art['image']}"
        print(f"  {art_id:>5}  card {card_id:<4}  {english_name(card):<24}  {reason}")


def choose_missing_card(items):
    print_missing(items)
    while items:
        value = input("\nArt id to generate (or q): ").strip()
        if value.lower() in {"q", "quit", "exit"}:
            return None
        try:
            art_id = int(value)
        except ValueError:
            print("Please enter an art id from the list.")
            continue
        for item in items:
            if item[2] == art_id:
                return item
        print(f"No missing art card with art id {art_id}.")
    return None


def choose_prompt(card, art, prompt_model, prompt_max_output_tokens):
    prompts = propose_prompts(card, art, prompt_model, prompt_max_output_tokens)
    while True:
        print("\nProposed prompts:")
        for index, prompt in enumerate(prompts, start=1):
            print(f"\n[{index}]\n{prompt}")
        choice = input("\nChoose 1-3, [a 1-3]ppend, [e]dit, [r]eroll, [n]o: ").strip().lower()
        if choice in {"1", "2", "3"}:
            return prompts[int(choice) - 1]
        append_match = re.fullmatch(r"a(?:ppend)?\s+([1-3])", choice)
        if append_match:
            prompt_index = int(append_match.group(1)) - 1
            addition = input(f"Append to prompt {prompt_index + 1}: ").strip()
            if addition:
                prompts[prompt_index] = f"{prompts[prompt_index].rstrip()} {addition}"
            continue
        if choice in {"n", "no", "q", "quit"}:
            return None
        if choice in {"r", "reroll"}:
            prompts = propose_prompts(card, art, prompt_model, prompt_max_output_tokens)
            continue
        if choice in {"e", "edit"}:
            edited = input("Paste edited prompt: ").strip()
            if edited:
                return edited
            continue
        print("Please choose 1, 2, 3, a 1, a 2, a 3, e, r, or n.")


def is_optional_parameter_error(exc, keys):
    message = str(exc).lower()
    return (
        keys
        and any(key in message for key in keys)
        and any(marker in message for marker in ("unknown", "unsupported", "unexpected"))
    )


def generate_image(prompt, outfile, model, size, quality):
    client = require_openai_client()
    request = {
        "model": model,
        "prompt": prompt,
        "size": size,
    }
    optional_keys = set()
    if quality:
        request["quality"] = quality
        optional_keys.add("quality")

    try:
        result = client.images.generate(**request)
    except Exception as exc:
        if not is_optional_parameter_error(exc, optional_keys):
            raise
        for key in optional_keys:
            request.pop(key, None)
        result = client.images.generate(**request)

    image = result.data[0]

    if getattr(image, "b64_json", None):
        outfile.write_bytes(base64.b64decode(image.b64_json))
        return

    raise SystemExit("The image API response did not contain base64 image data.")


def find_art_block(lines, art_id):
    card_re = re.compile(r"^  \d+:\s*$")
    art_re = re.compile(r"^      (\d+):\s*$")
    in_art_section = False

    for index, line in enumerate(lines):
        if re.match(r"^    art:\s*$", line):
            in_art_section = True
            continue
        if in_art_section and card_re.match(line):
            in_art_section = False
        if not in_art_section:
            continue
        match = art_re.match(line)
        if match and int(match.group(1)) == art_id:
            end = index + 1
            while end < len(lines):
                if art_re.match(lines[end]) or card_re.match(lines[end]):
                    break
                end += 1
            return index, end
    raise ValueError(f"Could not find art id {art_id} in {CARDS_FILE}.")


def update_cards_yaml(art_id, image_name, attribution):
    lines = CARDS_FILE.read_text(encoding="utf8").splitlines(keepends=True)
    start, end = find_art_block(lines, art_id)

    image_line = None
    attribution_line = None
    for index in range(start + 1, end):
        stripped = lines[index].strip()
        if stripped.startswith("image:"):
            image_line = index
        elif stripped.startswith("attribution:"):
            attribution_line = index

    if image_line is None:
        lines.insert(start + 1, f"        image: {image_name}\n")
        if attribution_line is not None:
            attribution_line += 1
    else:
        lines[image_line] = f"        image: {image_name}\n"

    if attribution_line is None:
        insert_at = (image_line + 1) if image_line is not None else (start + 2)
        lines.insert(insert_at, f"        attribution: {attribution}\n")
    elif not lines[attribution_line].split(":", 1)[1].strip().strip("'\""):
        lines[attribution_line] = f"        attribution: {attribution}\n"

    CARDS_FILE.write_text("".join(lines), encoding="utf8")


def preview_filename(card, art_id):
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{slugify(english_name(card))}_{art_id}_{timestamp}.png"


def open_preview(preview_path):
    try:
        result = subprocess.run(
            ["xdg-open", str(preview_path)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        print("Could not find xdg-open. Open the preview path manually.")
        return
    if result.returncode:
        print("xdg-open could not open the preview. Open the preview path manually.")


def approve_preview(preview_path):
    print(f"\nPreview image saved to: {preview_path}")
    print("Open that file to inspect it before adding it to cards.yaml.")
    while True:
        choice = input("Preview action: [o]pen, [y]es add, [n]o keep, [d]elete: ").strip().lower()
        if choice in {"o", "open"}:
            open_preview(preview_path)
            continue
        if choice in {"y", "yes"}:
            return "add"
        if choice in {"n", "no", "q", "quit"}:
            return "keep"
        if choice in {"d", "delete"}:
            preview_path.unlink(missing_ok=True)
            return "delete"
        print("Please choose o, y, n, or d.")


def generate_for_item(
    item,
    model,
    prompt_model,
    prompt_max_output_tokens,
    size,
    quality,
    overwrite=False,
):
    _card_id, card, art_id, art = item
    prompt = choose_prompt(card, art, prompt_model, prompt_max_output_tokens)
    if not prompt:
        print("Cancelled.")
        return None

    filename = f"{slugify(english_name(card))}_{art_id}.png"
    outfile = CLIENT_DIR / filename
    if outfile.exists() and not overwrite:
        raise SystemExit(f"{outfile} already exists. Use --overwrite to replace it.")

    PREVIEW_DIR.mkdir(exist_ok=True)
    preview_path = PREVIEW_DIR / preview_filename(card, art_id)

    quality_label = f", quality {quality}" if quality else ""
    print(f"\nGenerating preview image with {model}, API size {size}{quality_label}...")
    generate_image(prompt, preview_path, model, size, quality)

    action = approve_preview(preview_path)
    if action == "keep":
        print("Kept preview; cards.yaml was not updated.")
        return None
    if action == "delete":
        print("Deleted preview; cards.yaml was not updated.")
        return None

    shutil.move(str(preview_path), outfile)
    update_cards_yaml(art_id, filename, f"leovt and openai {dt.date.today().year}")
    print(f"Saved client/{filename} and updated cards.yaml.")
    return True


def resolve_item(data, requested_id):
    if requested_id is None:
        return choose_missing_card(list(missing_art_cards(data)))

    requested_id = int(requested_id)
    for item in iter_art_cards(data):
        card_id, _card, art_id, _art = item
        if requested_id in {card_id, art_id}:
            return item
    raise SystemExit(f"No card or art card found for id {requested_id}.")


def generate_loop(args):
    requested_id = args.id
    while True:
        data = load_cards()
        item = resolve_item(data, requested_id)
        requested_id = None
        if item is None:
            return

        generate_for_item(
            item,
            args.model,
            args.prompt_model,
            args.prompt_max_output_tokens,
            args.size,
            args.quality,
            args.overwrite,
        )


def main(argv=None):
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", default="generate")
    parser.add_argument("id", nargs="?", help="card id or art id to generate")
    parser.add_argument("--model", default=os.environ.get("OPENAI_IMAGE_MODEL", DEFAULT_MODEL))
    parser.add_argument("--prompt-model", default=os.environ.get("OPENAI_PROMPT_MODEL", DEFAULT_PROMPT_MODEL))
    parser.add_argument(
        "--prompt-max-output-tokens",
        type=int,
        default=int(os.environ.get("OPENAI_PROMPT_MAX_OUTPUT_TOKENS", DEFAULT_PROMPT_MAX_OUTPUT_TOKENS)),
    )
    parser.add_argument("--size", default=os.environ.get("OPENAI_IMAGE_SIZE", DEFAULT_SIZE))
    parser.add_argument("--quality", default=os.environ.get("OPENAI_IMAGE_QUALITY", DEFAULT_QUALITY))
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)

    commands = {"list", "prompt", "generate"}
    if args.command not in commands:
        if args.id is not None:
            parser.error(f"unknown command: {args.command}")
        args.id = args.command
        args.command = "generate"

    if args.command == "list":
        data = load_cards()
        print_missing(list(missing_art_cards(data)))
        return 0

    if args.command == "prompt":
        data = load_cards()
        item = resolve_item(data, args.id)
        if item is None:
            return 0
        _card_id, card, _art_id, art = item
        for index, prompt in enumerate(
            propose_prompts(card, art, args.prompt_model, args.prompt_max_output_tokens),
            start=1,
        ):
            print(f"[{index}] {prompt}\n")
        return 0

    generate_loop(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
