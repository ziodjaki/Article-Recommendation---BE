# Backend Journal Recommender (FastAPI + Gemini)

## Ringkasan
Backend ini menyediakan API rekomendasi jurnal berbasis semantic similarity dengan alur:
1. Parse sumber markdown jurnal ke `app/data/journals.json`.
2. Generate embedding jurnal dan simpan cache ke `app/data/embeddings.json`.
3. Hitung skor kemiripan query (judul + abstrak) terhadap jurnal.
4. Ambil Top K jurnal dan buat alasan rekomendasi.

Jika Gemini API tidak tersedia, sistem otomatis fallback ke embedding lokal hashing + keyword-based reason.

## Setup
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
```

Salin `.env.example` menjadi `.env`, lalu isi API key:
```env
GEMINI_API_KEY=isi_api_key_anda
GEMINI_MODEL=gemini-2.5-pro
GEMINI_EMBEDDING_MODEL=text-embedding-004
TOP_K=3
MIN_CONFIDENCE=0.35
JOURNAL_SOURCE_PATH=../jurnal.md
ALLOWED_ORIGINS=http://localhost:3000
ALLOWED_HOSTS=localhost,127.0.0.1,testserver
ENFORCE_API_KEY=false
API_KEYS=
RATE_LIMIT_REQUESTS=30
RATE_LIMIT_WINDOW_SECONDS=60
MAX_REQUEST_SIZE_BYTES=120000
TRUST_PROXY_HEADERS=false
```

### Security Layer (Production)
- Trusted host filtering lewat `ALLOWED_HOSTS` untuk mengurangi host header abuse.
- CORS allow-list ketat lewat `ALLOWED_ORIGINS`.
- Security headers aktif secara default (`X-Frame-Options`, `CSP`, `nosniff`, dll).
- Rate limiting endpoint `/recommend` berbasis IP (`RATE_LIMIT_REQUESTS` per `RATE_LIMIT_WINDOW_SECONDS`).
- Batas ukuran body request (`MAX_REQUEST_SIZE_BYTES`) untuk mengurangi abuse dan payload flooding.
- `Content-Type` endpoint `/recommend` dipaksa `application/json` untuk mengurangi request smuggling/format abuse.
- Validasi payload ketat (panjang field, karakter kontrol ditolak, extra field ditolak).
- API key guard opsional (`ENFORCE_API_KEY=true`, isi `API_KEYS` dengan pemisah koma).
- Header `X-Forwarded-For` hanya dipercaya jika `TRUST_PROXY_HEADERS=true` (aktifkan hanya jika di belakang reverse proxy tepercaya).

Untuk deployment publik, sangat disarankan:
1. Jalankan API di belakang reverse proxy (Nginx/Caddy/Cloudflare).
2. Aktifkan TLS (HTTPS only).
3. Set `ENFORCE_API_KEY=true` jika endpoint tidak sepenuhnya public.
4. Batasi `ALLOWED_ORIGINS` hanya domain frontend produksi.
5. Tambahkan WAF dan monitoring alert untuk anomali trafik.

## Menjalankan API
```powershell
.\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

Endpoint:
- `GET /health`
- `POST /recommend`
- `GET /docs`

## Menjalankan Test
```powershell
.\.venv\Scripts\python -m pytest -q
```
