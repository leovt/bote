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
    "No text, no numbers, no sigils, no symbols, no logos, no card border, no watermark, no UI elements."
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
        "a volcanic crater rim at night, glowing fissures, ash-laden wind, and hellish sky",
        "a sacked city street with broken gates, scattered embers, and dark smoke columns",
        "iron mine tunnels lit by forge-fire, rough-hewn walls, and the clang of metal",
    ],
    "green": [
        "deep woodland with mossy stones, roots, filtered light, and natural greens",
        "misty hills, old trees, wet earth, and a cool dawn atmosphere",
        "overgrown ruins reclaimed by vines, ferns, and dappled sunlight",
        "wild meadow at the forest edge with rocks, clouds, and restless wind",
        "ancient grove with massive trunks, mushrooms, lichen, and muted earth tones",
        "a river delta at low tide, tangled mangroves, mud banks, and wide grey sky",
        "a highland bog with peat, bracken, scattered stones, and low rolling fog",
        "a canopy high above the forest floor, broad leaves, shafts of light, bird calls implied",
        "a rain-soaked jungle clearing, dripping fronds, exposed roots, and heavy air",
    ],
    "blue": [
        "sea cliffs at dusk, crashing waves, salt spray, and a pale horizon",
        "a flooded archive or library with still water, lanterns, and drifting pages",
        "high mountain pass with ice, thin air, distant glaciers, and pale sky",
        "a coastal tower in fog, wet stone, seabirds, and a cold grey sea",
        "deep ocean ruins half-lit by bioluminescent growths",
        "an observatory terrace at night with star charts, brass instruments, and open sky",
        "a frozen tundra at midwinter, low sun, long blue shadows, and silence",
        "a storm-swept harbor with torn sails, churning water, and lightning in the distance",
    ],
    "black": [
        "a fog-filled marsh at midnight, dead trees, still water, and pale moonlight",
        "a plague-city alley with crumbling plaster, ravens, and shadow-heavy architecture",
        "a catacomb interior with carved stone, bone-white walls, and guttering torches",
        "a sunken ruin beneath a dead forest, roots cracking the stone",
        "a windswept graveyard with iron gates, overgrown headstones, and heavy clouds",
        "a corrupted shrine choked by black moss, dripping stone, and dim supernatural light",
        "a moonless river gorge, slick black rock, poisonous mist, and absolute quiet",
        "a collapsed tower interior, debris, cobwebs, and a single shaft of cold light",
    ],
    "white": [
        "sun-bleached cliffs and a fortified city on a plateau under a clear sky",
        "a vast marble courtyard with long shadows and a high noon sun",
        "a hilltop monastery with carved arches, white stone, and distant plains",
        "a wheat-field battlefield strewn with white banners and soft morning light",
        "an open plains landscape with wind-bent grass, wide sky, and distant mountains",
        "a cathedral interior with high vaults, dusty shafts of light, and carved reliefs",
        "a mountain citadel above the clouds, cold air, crisp light, and snow-dusted stone",
        "a ceremonial road lined with stone pillars, worn smooth, under a pale overcast sky",
    ],
    "source": [
        "a primal landscape vista with dramatic natural forces and atmospheric depth",
        "an ancient shrine integrated into the landscape, quiet but powerful",
        "a wide cinematic environment with elemental energy implied through light and weather",
        "a windswept clifftop above a sea of clouds, vast and silent",
    ],
    "neutral": [
        "weathered stone architecture, worn banners, and moody natural light",
        "a windswept landscape with ruins, cliffs, and a grounded fantasy tone",
        "a dramatic but believable environment with varied materials and restrained color",
        "a market square or town square at dusk, cobblestones, lanterns, and long shadows",
    ],
}
MEDIUM_VARIANTS = [
    "oil-painting inspired digital art with textured brushwork",
    "ink-and-wash fantasy illustration with selective color",
    "classic adventure-book cover painting with cinematic depth",
    "semi-realistic concept art with crisp silhouettes and painterly detail",
    "gouache-like fantasy illustration with matte colors and strong shapes",
    "watercolor fantasy illustration with soft bleeds and translucent washes",
    "Art Nouveau-inspired digital painting with organic lines and decorative atmosphere",
    "dramatic chiaroscuro oil painting with strong shadows and warm highlights",
    "engraving-style fantasy illustration with cross-hatching and high contrast",
    "plein-air landscape painting with loose brushwork and natural light",
    "woodcut-inspired illustration with bold outlines and flat texture planes",
    "pastel concept art with soft gradients and restrained color harmony",
    "dark fantasy acrylic painting with thick impasto texture and moody palette",
    "cinematic matte painting with photorealistic depth and atmospheric perspective",
]
MOOD_VARIANTS = [
    "at golden hour, long warm shadows",
    "under overcast midday light, flat and dramatic",
    "at dawn, cool mist and emerging light",
    "at dusk, deep shadows and saturated sky",
    "by torchlight or firelight in near-darkness",
    "under a storm sky with diffuse silvery light",
    "in bright high-altitude noon, bleached and sharp",
    "at night under a full moon, cool blues and sharp contrasts",
]
STEP_STYLE_CHOICES = [
    "oil-painting inspired fantasy realism with textured brushwork",
    "semi-realistic cinematic concept art with crisp silhouettes",
    "ink-and-wash fantasy illustration with restrained color",
    "gouache-like storybook fantasy art with matte colors",
    "classic adventure-book cover painting with dramatic depth",
    "moody dark-fantasy illustration with grounded materials",
    "watercolor fantasy illustration with soft bleeds and translucent washes",
    "Art Nouveau-inspired digital painting with organic lines and decorative atmosphere",
    "dramatic chiaroscuro oil painting with strong shadows and warm highlights",
    "engraving-style fantasy illustration with cross-hatching and high contrast",
    "woodcut-inspired illustration with bold outlines and flat texture planes",
    "cinematic matte painting with photorealistic depth and atmospheric perspective",
    "dark fantasy acrylic painting with thick impasto texture and moody palette",
    "pastel concept art with soft gradients and restrained color harmony",
]
STEP_ENVIRONMENT_CHOICES = [
    "basalt cliffs, smoke, black rock, and distant ember light",
    "deep woodland with mossy stones, old roots, and filtered light",
    "overgrown ruins with weathered stone, vines, and broken pillars",
    "windswept highland battlefield with banners, dust, and storm clouds",
    "ancient shrine integrated into a wild landscape",
    "wide primal landscape with elemental weather and atmospheric depth",
    "sea cliffs at dusk, crashing waves, salt spray, and a pale horizon",
    "fog-filled marsh at midnight, dead trees, still water, and pale moonlight",
    "sun-bleached plateau with a fortified city under a clear sky",
    "high mountain pass with ice, thin air, and distant glaciers",
    "catacomb interior with carved stone and guttering torches",
    "vast marble courtyard with long shadows under a high noon sun",
    "deep ocean ruins half-lit by bioluminescent growths",
    "rain-soaked jungle clearing, dripping fronds, exposed roots, and heavy air",
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


def describe_card_for_gpt_prompt(card):
    bits = [card["type"]]
    if card.get("subtypes"):
        bits.append(" ".join(card["subtypes"]))
    return ", ".join(bits)


def strength_word(card):
    if card.get("type") != "creature":
        return None
    if "strength" not in card or "toughness" not in card:
        return None
    total = card["strength"] + card["toughness"]
    if total >= 6:
        return "very strong"
    if total >= 4:
        return "quite strong"
    return "rather weak"


def step_prompt_subject_line(card):
    bits = [english_name(card), card["type"]]
    if card.get("subtypes"):
        bits.append(" ".join(card["subtypes"]))
    strength = strength_word(card)
    if strength:
        bits.append(strength)
    return ", ".join(bits)


def sanitized_rules_for_gpt_prompt(card):
    rules = []
    if card.get("effect"):
        rules.append(card["effect"])
    rules.extend(card.get("effects", []))
    for ability in card.get("abilities", []):
        if "keyword" in ability:
            rules.append(ability["keyword"])
        elif "effect" in ability:
            rules.append(ability["effect"])
    text = "; ".join(rules)
    text = re.sub(r"\{[^}]*\}", "", text)
    text = re.sub(r"\[[^\]]*\]", "", text)
    text = re.sub(r"\([^)]*\)", "", text)
    text = re.sub(r"\b\d+\b", "", text)
    text = re.sub(r"\b[A-Z]\b", "", text)
    text = text.replace(".", " ")
    text = re.sub(r"[+*/=]", " ", text)
    return " ".join(text.split())


def final_image_prompt(prompt):
    return f"{prompt.rstrip(' .')}. {FINAL_IMAGE_INSTRUCTIONS}"


def choose_from_menu(title, choices, free_label):
    print(f"\n{title}:")
    for index, choice in enumerate(choices, start=1):
        print(f"  [{index}] {choice}")
    while True:
        value = read_input(f"Choose 1-{len(choices)} or write {free_label}: ")
        if value is None:
            return None
        value = value.strip()
        if not value:
            continue
        if value.isdigit():
            index = int(value)
            if 1 <= index <= len(choices):
                return choices[index - 1]
            print(f"Please choose a number between 1 and {len(choices)}, or write {free_label}.")
            continue
        return value


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
    rules = sanitized_rules_for_gpt_prompt(card)
    details = [f"Card name: {name}", f"Card details: {describe_card_for_gpt_prompt(card)}"]
    if card.get("token"):
        details.append(
            "This is token creature art: keep the scene plain, simple, and low texture detail."
        )
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
            "Use the card name, type, abilities, and flavor as creative inspiration. "
            "Choose a distinctive art style suited to the card — draw from a wide range: "
            "oil painting, watercolor, ink-and-wash, engraving, gouache, chiaroscuro, "
            "Art Nouveau, woodcut, matte painting, plein-air, or others. "
            "Non-Western and atypical fantasy aesthetics (East Asian ink painting, "
            "Byzantine mosaic-inspired, Nordic woodcut, Mesoamerican relief) are encouraged when they fit. "
            "Specify a concrete environment with atmosphere, materials, and lighting. "
            "Include a mood and time of day (dawn, dusk, noon, night, overcast, torchlit, etc.). "
            "Do not use any existing character, franchise, artist name, logo, or copyrighted setting. "
            "Do not mention text, letters, numbers, sigils, runes, emblems, card UI, frames, borders, "
            "hands, game pieces, tabletop objects, or anything outside the fictional scene. "
            "Do not include numeric stats, costs, quantities, or rules syntax. "
            "Do not include aspect-ratio instructions. "
            "If the card is a token, keep the scene plain, simple, and low in texture detail. "
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


def improve_gpt_prompt(prompt, instruction, prompt_model, prompt_max_output_tokens):
    client = require_openai_client()
    optional_keys = set()
    improvement_instruction = "improve this image generation prompt"
    if instruction:
        improvement_instruction += f", {instruction}"
    request = {
        "model": prompt_model,
        "instructions": (
            "Improve the supplied image-generation prompt for original fantasy card game artwork. "
            "Preserve the core subject and constraints. "
            "Keep it concise and directly usable as an image-generation prompt. "
            "Do not introduce existing characters, franchises, artist names, logos, copyrighted settings, "
            "text, letters, numbers, sigils, symbols, card UI, borders, or watermarks. "
            "Return only the improved prompt."
        ),
        "input": f"{improvement_instruction} {prompt}",
        "max_output_tokens": prompt_max_output_tokens,
    }
    if prompt_model.startswith("gpt-5"):
        request["reasoning"] = {"effort": "minimal"}
        request["text"] = {"verbosity": "low"}
        optional_keys.update({"reasoning", "text"})

    try:
        response = client.responses.create(**request)
    except Exception as exc:
        if not is_optional_parameter_error(exc, optional_keys):
            raise
        for key in optional_keys:
            request.pop(key, None)
        response = client.responses.create(**request)
    improved = response_text(response)
    if not improved:
        raise SystemExit(
            "The prompt-improvement API response did not contain text. "
            f"Response summary: {response_summary(response)}"
        )
    return improved


def token_subject(card, art):
    color = card.get("color") or art.get("frame") or ""
    subtypes = card.get("subtypes", [])
    if "goblin" in subtypes:
        return "plain goblin"
    if subtypes:
        subject = " ".join([color, subtypes[0], "creature"])
    else:
        subject = " ".join([color, english_name(card), "creature"])
    return " ".join(subject.split())


def propose_token_prompt(card, art):
    subject = token_subject(card, art)
    landscape = random.choice([
        "a rocky plain landscape",
        "a barren rocky foothill landscape",
        "a sparse stone plain with low hills",
        "a simple rocky landscape with open sky",
    ])
    prompt = (
        f"A fantasy card game illustration of a {subject}. "
        f"It is a token creature, so use low texture simple art, one creature in {landscape}."
    )
    if "goblin" in card.get("subtypes", []):
        prompt += " Low emphasis on nose and ears."
    return final_image_prompt(prompt)


def propose_local_prompt(card, art):
    if card.get("token"):
        return propose_token_prompt(card, art)

    frame = art.get("frame") or card.get("color") or "neutral"
    frame_styles = STYLE_VARIANTS.get(frame, STYLE_VARIANTS["neutral"])
    environment = random.choice(frame_styles)
    medium = random.choice(MEDIUM_VARIANTS)
    mood = random.choice(MOOD_VARIANTS)
    flavour = art.get("flavour", {}).get("en", "")
    rules = card_rules(card)

    subject = step_prompt_subject_line(card)
    details = [f"Subject: {subject}."]
    if rules:
        details.append(f"Game mechanics to interpret visually: {rules}.")
    if flavour:
        details.append(f"Flavor mood: {flavour}.")

    prompt = " ".join([
        f"Create original fantasy trading-card artwork, {medium}.",
        *details,
        f"Environment: {environment}, {mood}.",
    ])
    return final_image_prompt(prompt)


def propose_step_prompt(card, art):
    style = choose_from_menu("Style", STEP_STYLE_CHOICES, "a custom style")
    if style is None:
        return None
    environment = choose_from_menu(
        "Environment and background",
        STEP_ENVIRONMENT_CHOICES,
        "a custom environment",
    )
    if environment is None:
        return None

    prompt = "\n".join([
        f"Create original fantasy trading-card artwork, {step_prompt_subject_line(card)}.",
        f"Style: {style}.",
        f"Environment and background: {environment}.",
    ])
    if card.get("token"):
        prompt += "\nToken creature art: keep the scene plain, simple, and low texture detail."
    return final_image_prompt(prompt)


def propose_prompts(card, art, local_count=2):
    prompts = []
    seen = set(prompts)
    while len(prompts) < local_count:
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


def read_input(prompt):
    try:
        return input(prompt)
    except (KeyboardInterrupt, EOFError):
        print()
        return None


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
        value = read_input("\nArt id to generate (or q): ")
        if value is None:
            return None
        value = value.strip()
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
    prompts = propose_prompts(card, art)
    while True:
        print("\nProposed prompts:")
        for index, prompt in enumerate(prompts, start=1):
            print(f"\n[{index}]\n{prompt}")
        choice = read_input(
            "\nChoose number, [s]tep prompt, [g]pt prompt, [a N]ppend, [i N]mprove, [e]dit, [r]eroll, [n]o: "
        )
        if choice is None:
            return None
        choice = choice.strip().lower()
        if choice.isdigit() and 1 <= int(choice) <= len(prompts):
            return prompts[int(choice) - 1]
        append_match = re.fullmatch(r"a(?:ppend)?\s+(\d+)", choice)
        if append_match:
            prompt_index = int(append_match.group(1)) - 1
            if not 0 <= prompt_index < len(prompts):
                print(f"Please choose a prompt between 1 and {len(prompts)}.")
                continue
            addition = read_input(f"Append to prompt {prompt_index + 1}: ")
            if addition is None:
                return None
            addition = addition.strip()
            if addition:
                prompts[prompt_index] = f"{prompts[prompt_index].rstrip()} {addition}"
            continue
        improve_match = re.fullmatch(r"i(?:mprove)?\s+(\d+)", choice)
        if improve_match:
            prompt_index = int(improve_match.group(1)) - 1
            if not 0 <= prompt_index < len(prompts):
                print(f"Please choose a prompt between 1 and {len(prompts)}.")
                continue
            instruction = read_input("Optional improvement instruction: ")
            if instruction is None:
                return None
            instruction = instruction.strip()
            print(f"Improving prompt {prompt_index + 1} with {prompt_model}...")
            prompts.append(
                improve_gpt_prompt(
                    prompts[prompt_index],
                    instruction,
                    prompt_model,
                    prompt_max_output_tokens,
                )
            )
            continue
        if choice in {"g", "gpt", "llm"}:
            print(f"Generating one prompt with {prompt_model}...")
            prompts.append(propose_gpt_prompt(card, art, prompt_model, prompt_max_output_tokens))
            continue
        if choice in {"s", "step", "stepwise"}:
            prompt = propose_step_prompt(card, art)
            if prompt:
                prompts.append(prompt)
            continue
        if choice in {"n", "no", "q", "quit"}:
            return None
        if choice in {"r", "reroll"}:
            prompts = propose_prompts(card, art)
            continue
        if choice in {"e", "edit"}:
            edited = read_input("Paste edited prompt: ")
            if edited is None:
                return None
            edited = edited.strip()
            if edited:
                return edited
            continue
        print("Please choose a prompt number, s, g, a N, i N, e, r, or n.")


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
    if os.environ.get("TERM_PROGRAM") == "vscode":
        opener = ["code", str(preview_path)]
    else:
        opener = ["xdg-open", str(preview_path)]
    try:
        result = subprocess.run(
            opener,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        print(f"Could not find {opener[0]}. Open the preview path manually.")
        return
    if result.returncode:
        print(f"{opener[0]} could not open the preview. Open the preview path manually.")


def approve_preview(preview_path):
    print(f"\nPreview image saved to: {preview_path}")
    if os.environ.get("TERM_PROGRAM") == "vscode":
        open_preview(preview_path)
    else:
        print("Open that file to inspect it before adding it to cards.yaml.")
    while True:
        choice = read_input("Preview action: [o]pen, [y]es add, [n]o keep, [d]elete: ")
        if choice is None:
            return "keep"
        choice = choice.strip().lower()
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
        for index, prompt in enumerate(propose_prompts(card, art), start=1):
            print(f"[{index}] {prompt}\n")
        return 0

    generate_loop(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
