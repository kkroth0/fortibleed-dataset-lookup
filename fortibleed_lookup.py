#!/usr/bin/env python3
"""Cruza uma lista de domínios contra o dataset público do FortiBleed.

Dataset (uma entrada por linha):
    https://github.com/kkroth0/fortibleed-dataset-lookup

Uso:
    python3 fortibleed_lookup.py meus_dominios.txt
    python3 fortibleed_lookup.py meus_dominios.txt --dataset fortibleed-public-dataset.txt
    python3 fortibleed_lookup.py meus_dominios.txt --subdomains   # casa subdomínios também
    python3 fortibleed_lookup.py meus_dominios.txt --json resultado.json

Saída: lista os domínios do SEU arquivo que aparecem (HIT) no dataset.
Código de saída 1 se houve pelo menos um HIT, 0 caso contrário (útil em pipelines).
"""

from __future__ import annotations

import argparse
import json
import os
import sys


def normalize(raw: str) -> str:
    """Reduz uma linha a um domínio comparável.

    Remove BOM, espaços, esquema (http://), usuário, porta, caminho, 'www.',
    ponto final e deixa tudo minúsculo.
    """
    d = raw.strip().lstrip("﻿").strip()
    if not d or d.startswith("#"):
        return ""
    # remove esquema
    if "://" in d:
        d = d.split("://", 1)[1]
    # remove credenciais user@host
    if "@" in d:
        d = d.rsplit("@", 1)[1]
    # remove caminho / query
    for sep in ("/", "?", "#"):
        if sep in d:
            d = d.split(sep, 1)[0]
    # remove porta
    if ":" in d:
        d = d.split(":", 1)[0]
    d = d.strip().rstrip(".").lower()
    if d.startswith("www."):
        d = d[4:]
    return d


def load_domains(path: str) -> tuple[set[str], int]:
    """Carrega e normaliza domínios de um arquivo. Retorna (conjunto, linhas_lidas)."""
    domains: set[str] = set()
    lines = 0
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            lines += 1
            n = normalize(line)
            if n:
                domains.add(n)
    return domains, lines


def parent_domains(domain: str):
    """Gera os domínios-pai: a.b.c.com -> b.c.com -> c.com."""
    parts = domain.split(".")
    for i in range(len(parts) - 1):
        yield ".".join(parts[i:])


def find_default_dataset() -> str:
    """Procura o dataset ao lado do script ou no diretório atual."""
    name = "fortibleed-public-dataset.txt"
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), name),
        os.path.join(os.getcwd(), name),
        os.path.expanduser(os.path.join("~", "Downloads", name)),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return candidates[0]


def main() -> int:
    ap = argparse.ArgumentParser(description="Cruza domínios com o dataset FortiBleed.")
    ap.add_argument("input", help="Arquivo com os domínios a verificar (um por linha).")
    ap.add_argument(
        "--dataset",
        default=None,
        help="Caminho do dataset FortiBleed (default: procura fortibleed-public-dataset.txt).",
    )
    ap.add_argument(
        "--subdomains",
        action="store_true",
        help="Conta como HIT se um domínio-pai estiver no dataset (ex.: vpn.acme.com casa acme.com).",
    )
    ap.add_argument("--json", metavar="ARQUIVO", help="Grava o resultado completo em JSON.")
    ap.add_argument("-q", "--quiet", action="store_true", help="Mostra só os domínios que deram HIT.")
    args = ap.parse_args()

    dataset_path = args.dataset or find_default_dataset()

    for label, path in (("dataset", dataset_path), ("entrada", args.input)):
        if not os.path.isfile(path):
            print(f"ERRO: arquivo de {label} não encontrado: {path}", file=sys.stderr)
            return 2

    dataset, _ = load_domains(dataset_path)
    targets, target_lines = load_domains(args.input)

    hits = []   # (dominio_consultado, dominio_que_casou)
    misses = []
    for d in sorted(targets):
        if d in dataset:
            hits.append((d, d))
        elif args.subdomains:
            matched = next((p for p in parent_domains(d) if p in dataset), None)
            if matched:
                hits.append((d, matched))
            else:
                misses.append(d)
        else:
            misses.append(d)

    if not args.quiet:
        print(f"Dataset:  {dataset_path}  ({len(dataset)} domínios únicos)")
        print(f"Entrada:  {args.input}  ({len(targets)} únicos / {target_lines} linhas)")
        print(f"Modo subdomínio: {'on' if args.subdomains else 'off'}")
        print("-" * 60)

    if hits:
        print(f"[!] {len(hits)} HIT(s) encontrados no dataset:")
        for queried, matched in hits:
            if queried == matched:
                print(f"    {queried}")
            else:
                print(f"    {queried}  (via {matched})")
    else:
        print("[ok] Nenhum domínio da entrada está no dataset.")

    if not args.quiet and misses:
        print(f"\n[-] {len(misses)} sem correspondência.")

    if args.json:
        payload = {
            "dataset": dataset_path,
            "dataset_count": len(dataset),
            "input": args.input,
            "input_count": len(targets),
            "subdomain_match": args.subdomains,
            "hits": [{"queried": q, "matched": m} for q, m in hits],
            "misses": misses,
        }
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
        if not args.quiet:
            print(f"\nJSON gravado em {args.json}")

    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
