# Editorial Teardown Engine - Complete Architecture

## Overview

This system analyzes LinkedIn profiles and posts, generates editorial verdicts, and creates hand-drawn style annotations on screenshots to use in personalized outreach emails.

**Goal:** Make output look like "a senior hiring manager marked this up by hand" — not AI annotations.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        PHASE 1: DATA COLLECTION                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   LinkedIn URL → Apify Scraper → Profile Data + Posts Data           │
│                         ↓                                            │
│              Selenium + undetected-chromedriver                      │
│                         ↓                                            │
│              Screenshots (Profile + Posts)                           │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    PHASE 2: EDITORIAL TEARDOWN                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   [1] Content Isolation                                              │
│       Raw Screenshot → Minimal Crop → clean_content.png              │
│                                                                      │
│   [2] Narrative Diagnosis (GPT-3.5-turbo, TEXT ONLY)                 │
│       OCR Text → Verdict + Core Gap + Consequence                    │
│                                                                      │
│   [3] Evidence Selection (Tesseract OCR + GPT-3.5-turbo)             │
│       OCR Elements → GPT Selection → Exact Coordinates               │
│                                                                      │
│   [4] Hand-Drawn Rendering (PIL/Pillow)                              │
│       Coordinates → Wobbly Circles + Arrows + Margin Notes           │
│                                                                      │
│   [5] Playbook Generation (GPT-3.5-turbo)                            │
│       Verdict → Why It Fails + The Fix + Before/After Rewrites       │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│                      PHASE 3: EMAIL GENERATION                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   Playbooks + Teardown Images → HTML Email with Embedded Images      │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Models Used

| Component | Model | Purpose |
|-----------|-------|---------|
| Profile/Post Scraping | Apify `apimaestro/linkedin-profile-detail` | Get profile data |
| Post Scraping | Apify `apimaestro/linkedin-profile-posts` | Get posts data |
| OCR Text Extraction | **Tesseract 5.5.1** (via pytesseract) | Extract text with exact pixel coordinates |
| Text Extraction from Images | **GPT-4o** (`gpt-4o`) | OCR fallback + image understanding |
| Narrative Diagnosis | **GPT-3.5-turbo** | Generate editorial verdicts (text-only) |
| Text Element Selection | **GPT-3.5-turbo** | Select which OCR elements prove verdict |
| Playbook Generation | **GPT-3.5-turbo** | Generate actionable playbooks |

---

## File Structure

```
outreach automaation/
├── main.py                    # Main orchestrator (Phase 1 + Phase 2)
├── config.py                  # API keys, model configs
├── 
├── ─── PHASE 1: DATA COLLECTION ───
├── apify_client.py            # Apify API wrapper for scraping
├── cookie_manager.py          # LinkedIn cookie management
├── linkedin_cookies.json      # Stored LinkedIn session cookies
├── 
├── ─── PHASE 2: EDITORIAL TEARDOWN ───
├── teardown_engine.py         # Main orchestrator for Phase 2
├── content_isolator.py        # Crop screenshots to content only
├── narrative_diagnosis.py     # Generate verdicts (GPT-3.5-turbo)
├── ocr_extractor.py           # Tesseract OCR with coordinates
├── text_matcher.py            # Match verdict to OCR elements (GPT)
├── evidence_selector.py       # Select evidence using OCR + GPT
├── hand_drawn_renderer.py     # Draw annotations (PIL)
├── playbook_generator.py      # Generate playbooks (GPT-3.5-turbo)
├── 
├── ─── PHASE 3: EMAIL ───
├── email_generator.py         # Generate HTML emails
├── 
├── ─── OUTPUT ───
└── output/
    └── {profile_id}/
        ├── profile_data.json
        ├── posts.json
        ├── posts_analysis.json
        ├── screenshot.png
        ├── post_screenshots/
        │   ├── post_1_*.png
        │   └── post_2_*.png
        ├── clean_content/
        │   ├── clean_profile.png
        │   └── clean_post_*.png
        ├── editorial_teardown/
        │   ├── profile_teardown.png
        │   ├── post_*_teardown.png
        │   ├── profile_playbook.txt
        │   └── post_*_playbook.txt
        ├── diagnoses.json
        ├── evidence.json
        ├── playbooks.json
        ├── outreach_email.html
        └── teardown_summary.json
```

---

## Module Details

### 1. Content Isolator (`content_isolator.py`)

**Purpose:** Crop screenshots to remove LinkedIn UI chrome (nav bars, sidebars, ads).

**Method:** Conservative cropping - just trims edges, keeps most content visible.

```python
# Key settings
PADDING = 40  # pixels
SKIP_CROP = True  # Minimal cropping

# For posts: trim left/right margins slightly
left_margin = min(50, int(width * 0.03))
right_margin = min(100, int(width * 0.05))
```

**Output:** `clean_content/clean_profile.png`, `clean_content/clean_post_*.png`

---

### 2. Narrative Diagnosis (`narrative_diagnosis.py`)

**Purpose:** Generate editorial verdicts using TEXT ONLY (no image analysis).

**Model:** `gpt-3.5-turbo`

**Input:** OCR-extracted text from screenshot

**Output Schema:**
```json
{
  "primary_story": "What this content is trying to say",
  "actual_signal": "What it actually signals to a stranger",
  "core_gap": "The single biggest mismatch",
  "consequence": "What this costs the user",
  "one_sentence_verdict": "Blunt verdict under 20 words"
}
```

**Quality Gates (auto-reject and regenerate):**
- Banned phrases: "no change needed", "add a hook", "improve engagement", "consider adding", etc.
- Verdict must be under 25 words
- Consequence must mention a real cost (words like "miss", "lose", "skip")

**Max Retries:** 3

---

### 3. OCR Extractor (`ocr_extractor.py`)

**Purpose:** Extract ALL text from image with EXACT pixel coordinates.

**Model:** Tesseract 5.5.1 (via pytesseract)

**Config:** `--psm 3` (default, block-level text)

**Output:**
```json
[
  {
    "text": "Mesa School of Business",
    "x1": 120,
    "y1": 45,
    "x2": 350,
    "y2": 72,
    "confidence": 92.5
  }
]
```

---

### 4. Text Matcher (`text_matcher.py`)

**Purpose:** Use GPT to select which OCR text elements prove the verdict.

**Model:** `gpt-3.5-turbo`

**Method:**
1. Group OCR words into lines (same y-position within 15px)
2. Filter out UI chrome (y < 60px, tiny elements)
3. Present numbered list of text candidates to GPT
4. GPT returns which element IDs prove the verdict
5. Return those elements with their exact coordinates

**Prompt:**
```
You are selecting which text elements prove an editorial verdict.

VERDICT: "{verdict}"
CORE GAP: {core_gap}

Here are the text elements found in the image:
1. "Mesa School of Business" (y=45)
2. "Young entrepreneur on a mission..." (y=180)
...

Select exactly 2 text elements that BEST PROVE the verdict.
Return: {"selected": [1, 5]}
```

---

### 5. Evidence Selector (`evidence_selector.py`)

**Purpose:** Orchestrate OCR + Text Matching to get final evidence with coordinates.

**Flow:**
```
Image → OCR Extractor → Text Elements
                            ↓
Verdict + Text Elements → Text Matcher → Selected Elements
                                              ↓
                                    Evidence with Coordinates
```

**Output:**
```json
{
  "evidence": [
    {
      "id": 1,
      "why_it_matters": "Matches: Element 5",
      "editorial_caption": "Self-promotional facade masks...",
      "bounding_box": {"x1": 505, "y1": 595, "x2": 1065, "y2": 609}
    }
  ],
  "evidence_strength": "strong",
  "verdict_supported": true
}
```

---

### 6. Hand-Drawn Renderer (`hand_drawn_renderer.py`)

**Purpose:** Draw annotations that look like a human marked it with a red pen.

**Visual Elements:**

| Element | Description |
|---------|-------------|
| Wobbly Rectangle | 4 overlapping rectangles with random jitter (±3px) |
| Wavy Underline | Zigzag line below text (step=6px, amplitude=3px) |
| Scribbled Arrow | Polyline with random offsets + arrowhead polygon |
| Margin Note | Text caption positioned to the right of the box |

**Colors:**
```python
RED = (196, 30, 58)   # Cardinal red for marks
BLACK = (26, 26, 26)  # For text
```

**Font:** Chalkboard (macOS) or fallback to system default

**Key Code:**
```python
def _draw_wobbly_circle(self, draw, bbox):
    x1, y1, x2, y2 = bbox
    for _ in range(4):  # Draw 4 overlapping rectangles
        jitter = 3
        draw.rectangle([
            self._wobble(x1, jitter),
            self._wobble(y1, jitter),
            self._wobble(x2, jitter),
            self._wobble(y2, jitter),
        ], outline=self.RED, width=2)

def _wobble(self, value, delta=3):
    return value + random.randint(-delta, delta)
```

---

### 7. Playbook Generator (`playbook_generator.py`)

**Purpose:** Generate actionable playbooks with specific rewrites.

**Model:** `gpt-3.5-turbo`

**Output Schema:**
```json
{
  "editorial_verdict": "One sentence verdict",
  "why_it_fails": ["Bullet 1", "Bullet 2", "Bullet 3"],
  "the_fix": "Shift from X to Y",
  "before_after": {
    "headline": {"before": "...", "after": "..."},
    "paragraph": {"before": "...", "after": "..."}
  },
  "reusable_principle": "If someone X, they should feel Y"
}
```

**Banned Phrases (auto-reject):**
- "consider adding"
- "you might want to"
- "best practice"
- "thought leader"
- "value proposition"
- "personal brand"

---

### 8. Teardown Engine (`teardown_engine.py`)

**Purpose:** Orchestrate the full Phase 2 pipeline.

**Flow:**
```python
def run(self):
    # Step 1: Content Isolation
    clean_content = isolate_all_content(self.profile_dir)
    
    # Step 2: Narrative Diagnosis
    diagnoses = diagnose_all_content(self.profile_dir, profile_data)
    
    # Step 3: Evidence Selection (OCR-based)
    evidence = select_evidence_for_all(self.profile_dir, diagnoses)
    
    # Step 4: Hand-Drawn Rendering
    rendered = self._render_hand_drawn(evidence)
    
    # Step 5: Playbook Generation
    playbooks = generate_all_playbooks(self.profile_dir, diagnoses, evidence)
    
    # Quality Check
    self._run_quality_checks()
```

**Quality Checks:**
- Clear one-sentence verdict (< 20 words)
- Passed quality gate (no banned phrases)
- Clear directional fix (contains "to")

---

## Data Flow Diagram

```
┌──────────────┐
│ LinkedIn URL │
└──────┬───────┘
       │
       ▼
┌──────────────┐     ┌──────────────┐
│ Apify Scrape │────▶│ Profile Data │
└──────┬───────┘     │ Posts Data   │
       │             └──────────────┘
       ▼
┌──────────────┐     ┌──────────────┐
│   Selenium   │────▶│ Screenshots  │
│ (cookies)    │     │ (PNG files)  │
└──────────────┘     └──────┬───────┘
                            │
       ┌────────────────────┴────────────────────┐
       ▼                                         ▼
┌──────────────┐                          ┌──────────────┐
│   Content    │                          │   Content    │
│   Isolator   │                          │   Isolator   │
└──────┬───────┘                          └──────┬───────┘
       │                                         │
       ▼                                         ▼
┌──────────────┐                          ┌──────────────┐
│ clean_profile│                          │ clean_post_* │
│    .png      │                          │    .png      │
└──────┬───────┘                          └──────┬───────┘
       │                                         │
       ▼                                         ▼
┌──────────────┐                          ┌──────────────┐
│  Tesseract   │                          │  Tesseract   │
│     OCR      │                          │     OCR      │
└──────┬───────┘                          └──────┬───────┘
       │                                         │
       ▼                                         ▼
┌──────────────┐                          ┌──────────────┐
│  OCR Text    │                          │  OCR Text    │
│  + Coords    │                          │  + Coords    │
└──────┬───────┘                          └──────┬───────┘
       │                                         │
       ├─────────────────┬───────────────────────┤
       │                 │                       │
       ▼                 ▼                       ▼
┌──────────────┐  ┌──────────────┐       ┌──────────────┐
│  Narrative   │  │    Text      │       │  Narrative   │
│  Diagnosis   │  │   Matcher    │       │  Diagnosis   │
│ (GPT-3.5)    │  │  (GPT-3.5)   │       │ (GPT-3.5)    │
└──────┬───────┘  └──────┬───────┘       └──────┬───────┘
       │                 │                       │
       ▼                 ▼                       ▼
┌──────────────┐  ┌──────────────┐       ┌──────────────┐
│   Verdict    │  │   Evidence   │       │   Verdict    │
│   + Gap      │  │  Coordinates │       │   + Gap      │
└──────┬───────┘  └──────┬───────┘       └──────┬───────┘
       │                 │                       │
       └────────┬────────┘                       │
                │                                │
                ▼                                ▼
         ┌──────────────┐                 ┌──────────────┐
         │  Hand-Drawn  │                 │  Hand-Drawn  │
         │   Renderer   │                 │   Renderer   │
         └──────┬───────┘                 └──────┬───────┘
                │                                │
                ▼                                ▼
         ┌──────────────┐                 ┌──────────────┐
         │   profile_   │                 │   post_*_    │
         │  teardown.png│                 │  teardown.png│
         └──────┬───────┘                 └──────┬───────┘
                │                                │
                └────────────┬───────────────────┘
                             │
                             ▼
                      ┌──────────────┐
                      │   Playbook   │
                      │  Generator   │
                      │  (GPT-3.5)   │
                      └──────┬───────┘
                             │
                             ▼
                      ┌──────────────┐
                      │   Email      │
                      │  Generator   │
                      └──────┬───────┘
                             │
                             ▼
                      ┌──────────────┐
                      │  outreach_   │
                      │  email.html  │
                      └──────────────┘
```

---

## API Keys & Configuration

**File:** `config.py`

```python
# Apify
APIFY_API_KEY = os.getenv("APIFY_API_KEY")
LINKEDIN_PROFILE_ACTOR = "apimaestro/linkedin-profile-detail"
LINKEDIN_POSTS_ACTOR = "apimaestro/linkedin-profile-posts"

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-3.5-turbo"           # For text analysis
OPENAI_VISION_MODEL = "gpt-4o"           # For image analysis (fallback)

# Agency
AGENCY_NAME = os.getenv("AGENCY_NAME")
AGENCY_EMAIL = os.getenv("AGENCY_EMAIL")
AGENCY_WEBSITE = os.getenv("AGENCY_WEBSITE")
```

**File:** `.env`
```
APIFY_API_KEY=apify_api_xxx
OPENAI_API_KEY=sk-proj-xxx
AGENCY_NAME=Your Agency
AGENCY_EMAIL=contact@agency.com
AGENCY_WEBSITE=https://agency.com
```

---

## Dependencies

**File:** `requirements.txt`

```
requests>=2.28.0
python-dotenv>=1.0.0
Pillow>=9.0.0
openai>=1.0.0
undetected-chromedriver>=3.5.0
selenium>=4.0.0
pytesseract>=0.3.10
```

**System Dependencies:**
- Tesseract OCR 5.5.1 (`brew install tesseract`)
- Chrome browser (for Selenium)

---

## Usage

### Full Pipeline (Phase 1 + Phase 2)
```bash
python main.py https://www.linkedin.com/in/username/
```

### Phase 2 Only (on existing data)
```bash
python teardown_engine.py output/username/
```

### Generate Email Only
```bash
python email_generator.py output/username/
```

---

## Output Example

**Verdict:** "Self-promotional facade masks lack of substance or meaningful impact."

**Why It Fails:**
- Focus on personal achievements instead of societal impact
- Superficial portrayal of commitment to social causes
- Lacks authenticity in connecting on a meaningful level

**The Fix:** "Shift from self-centered promotion to genuine dedication to impactful social causes."

**Before → After:**
- **Before:** "Mesa School of Business"
- **After:** "Passionate Entrepreneur Driving Social Change"

**Reusable Principle:** "If someone showcases genuine dedication to social causes, they should feel connected on a deeper and more meaningful level."

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| V0 | Dec 2024 | Initial vision-based annotation (inaccurate boxes) |
| V1 | Dec 2024 | OCR-based coordinates + hand-drawn rendering |
| V1.1 | Dec 2024 | Added UI chrome filtering, improved text matching |
| **V2** | Dec 2024 | **Judgment-First Architecture with Claude 3.5 Sonnet Vision** |

---

# V2: JUDGMENT-FIRST EDITORIAL ENGINE

## New Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    V2: JUDGMENT-FIRST ARCHITECTURE                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   Raw Screenshot                                                     │
│        ↓                                                             │
│   [Claude 3.5 Sonnet Vision] ─── "Brutal Executive Editor" Persona  │
│        ↓                                                             │
│   Strict JSON Output:                                                │
│     • verdict (3-6 words)                                            │
│     • the_gap (2 sentences)                                          │
│     • annotations (EXACTLY 2, with normalized bounding boxes)        │
│        ↓                                                             │
│   [PIL Hand-Drawn Renderer]                                          │
│     • Wobbly ellipses                                                │
│     • Leader lines to margin                                         │
│     • Handwritten-style notes                                        │
│     • Verdict box at top                                             │
│        ↓                                                             │
│   Editorial Teardown Image                                           │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Key Difference: V1 vs V2

| Aspect | V1 (OCR + GPT-3.5) | V2 (Claude Vision) |
|--------|-------------------|-------------------|
| Analysis | Text-only after OCR | Direct image understanding |
| Coordinates | Tesseract → GPT matching | Claude returns normalized bbox |
| Model | GPT-3.5-turbo | Claude 3.5 Sonnet |
| Annotations | Up to 3 | EXACTLY 2 |
| Persona | General analysis | "Brutal Executive Editor" |
| Output | Tips & issues | Diagnosis & observations |

## V2 Model

| Component | Model | Purpose |
|-----------|-------|---------|
| Vision Analysis + Coordinates | **Claude 3.5 Sonnet** (`claude-sonnet-4-20250514`) | Single-pass analysis with bounding boxes |

## V2 Output Schema (Pydantic)

```python
class Annotation(BaseModel):
    text_snippet: str      # Exact text in that area
    editorial_note: str    # Blunt observation (max 12 words)
    bounding_box: List[float]  # [ymin, xmin, ymax, xmax] normalized 0-1

class EditorialOutput(BaseModel):
    verdict: str           # 3-6 word punchy headline
    the_gap: str           # 2 sentences: what they project + why it fails
    annotations: List[Annotation]  # EXACTLY 2 high-impact annotations
```

## V2 Rendering Features

| Element | Description |
|---------|-------------|
| Verdict Box | Dark background at top, bold white text |
| Wobbly Ellipse | 3 overlapping ellipses with random wobble |
| Leader Line | Scribbled line from ellipse to margin |
| Numbered Circle | Red circle with white number |
| Margin Note | Handwritten-style text (Chalkboard/Marker Felt font) |

## V2 Usage

```bash
# Single image
python editorial_engine.py screenshot.png output.png

# Process entire profile folder
python editorial_engine.py --folder output/jainjatin2525
```

## V2 File

- `editorial_engine.py` - Complete standalone module

---

## Success Criteria

The user reaction should be:
> "Damn. That's exactly what's wrong."

Not:
> "Okay, makes sense."

If it doesn't sting a little, it's not good enough.

