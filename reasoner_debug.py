from app.config import Settings
from app.services.reasoner import ReasonerService
import json

settings = Settings()
reasoner = ReasonerService(settings)

title = 'VOICING HYBRIDITY: A CRITICAL DISCOURSE ANALYSIS OF CODE-SWITCHING AND IDENTITY CONSTRUCTION AMONG THIRD-CULTURE YOUTH ON SOCIAL MEDIA'
abstract = 'Third-Culture Youth (TCY), a growing global demographic, navigate complex hybrid identities. Their use of code-switching (CS) on social media a key “third space” is a central yet often misunderstood discursive practice, frequently stigmatized rather than analyzed as a sophisticated mechanism for identity construction. This research utilizes Critical Discourse Analysis (CDA) to investigate the specific functions of code-switching as a strategic discursive resource employed by TCYs to construct and perform hybrid identities in digitally-mediated environments. A qualitative, netnographic methodology was employed, analyzing public social media content (N=1,284 artifacts) from 45 purposively sampled TCY informants across Instagram, TikTok, and Twitter (X). Fairclough’s CDA framework was applied to link linguistic texts to social practices. Findings reveal CS is a normative practice (present in 82% of data). Two primary functions were identified: (1) In-Group Signaling to establish community boundaries, and (2) ‘Affective/Nuanced Expression’ to convey cultural-emotional concepts (e.g., natsukashii) deemed untranslatable in English. Code-switching is not a linguistic deficit but a sophisticated, learned mechanism for “voicing hybridity.” TCYs strategically deploy CS as a resilient social practice to perform a coherent ‘third culture’ identity, actively challenging dominant monolingual ideologies.'

with open('app/data/journals.json', 'r', encoding='utf-8') as f:
    journals = json.load(f)

for j in journals:
    overlap = sorted(reasoner._keyword_set(f"{title} {abstract}") & reasoner._keyword_set(j.get("full_text", "")))
    print(j['name'], '->', len(overlap), overlap)
