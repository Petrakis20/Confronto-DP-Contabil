#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
mapping_generator.py

Gera o arquivo mapping_eventos.json no formato:
{
    "LA1": ["Cód1", "Cód2", ...],
    "LA2": ["Cód3", ...],
    ...
}
a partir do arquivo eventos.txt.
"""

import re
import json
from pathlib import Path

def generate_mapping_json(input_path: Path, output_path: Path):
    mapping: dict[str, list[str]] = {}
    current_code: str | None = None
    seen: set[str] = set()

    with input_path.open('r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.rstrip('\n')
            # se linha inicia com código de evento (3 dígitos), começamos novo bloco
            header = re.match(r'^\s*(\d{3})\b', line)
            if header:
                current_code = header.group(1)
                seen.clear()
            if current_code:
                # extrai todos os tokens numéricos de ≥4 dígitos (LAs)
                for token in line.split():
                    if token.isdigit() and len(token) >= 4 and token not in seen:
                        mapping.setdefault(token, []).append(current_code)
                        seen.add(token)

    # grava o JSON
    with output_path.open('w', encoding='utf-8') as f:
        json.dump(mapping, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    base = Path(__file__).parent
    in_file = base / "eventos.txt"
    out_file = base / "mapping_eventos.json"
    generate_mapping_json(in_file, out_file)
    print(f"Arquivo gerado: {out_file}")
