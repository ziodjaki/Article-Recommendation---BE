from pathlib import Path
from app.services.parser import parse_file_to_json

parse_file_to_json(Path('../jurnal.md'), Path('app/data/journals.json'))
