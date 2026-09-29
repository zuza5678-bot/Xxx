"""Składa index.html z src.html i data.json (dane przykładowe jako zapas offline)."""
import json
seed = json.dumps(json.load(open('data.json', encoding='utf-8')), ensure_ascii=False).replace('</', '<\\/')
src = open('src.html', encoding='utf-8').read()
open('index.html', 'w', encoding='utf-8').write(src.replace('/*SEED*/', seed))
