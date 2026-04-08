import sys
import os
import json

from app.config import Settings
from app.services.embedding import EmbeddingService
from app.services.reasoner import ReasonerService
from app.services.recommender import RecommenderService

settings = Settings()
embedding_service = EmbeddingService(settings)
reasoner_service = ReasonerService(settings)
recommender = RecommenderService(settings, embedding_service, reasoner_service)

with open('app/data/journals.json', 'r', encoding='utf-8') as f:
    journals = json.load(f)

title = 'VOICING HYBRIDITY: A CRITICAL DISCOURSE ANALYSIS OF CODE-SWITCHING AND IDENTITY CONSTRUCTION AMONG THIRD-CULTURE YOUTH ON SOCIAL MEDIA'
abstract = 'Third-Culture Youth (TCY), a growing global demographic, navigate complex hybrid identities. Their use of code-switching (CS) on social media a key “third space” is a central yet often misunderstood discursive practice, frequently stigmatized rather than analyzed as a sophisticated mechanism for identity construction. This research utilizes Critical Discourse Analysis (CDA) to investigate the specific functions of code-switching as a strategic discursive resource employed by TCYs to construct and perform hybrid identities in digitally-mediated environments. A qualitative, netnographic methodology was employed, analyzing public social media content (N=1,284 artifacts) from 45 purposively sampled TCY informants across Instagram, TikTok, and Twitter (X). Fairclough’s CDA framework was applied to link linguistic texts to social practices. Findings reveal CS is a normative practice (present in 82% of data). Two primary functions were identified: (1) In-Group Signaling to establish community boundaries, and (2) ‘Affective/Nuanced Expression’ to convey cultural-emotional concepts (e.g., natsukashii) deemed untranslatable in English. Code-switching is not a linguistic deficit but a sophisticated, learned mechanism for “voicing hybridity.” TCYs strategically deploy CS as a resilient social practice to perform a coherent ‘third culture’ identity, actively challenging dominant monolingual ideologies.'

results = recommender.recommend(title=title, abstract=abstract, journals=journals)
for rec in results:
    print(f"Jurnal: {rec['journal_name']}, Score: {rec['score']} - {rec['confidence']}")
