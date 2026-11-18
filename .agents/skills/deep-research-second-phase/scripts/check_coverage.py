#!/usr/bin/env python3
"""Confere se um Deep Research Document preservou o material de origem.

Uso:
    python check_coverage.py --output documento.md --source pesquisa.md [--source outra.md ...]

O script não entende o texto. Ele compara itens objetivos que não deveriam sumir
numa reescrita (URLs, números, termos técnicos, trechos de código) e confere a
estrutura obrigatória do documento (cabeçalho e 16 seções, nome e ordem exatos).
Cada item apontado como ausente precisa ser conferido: pode ser uma perda real ou
apenas uma mudança de forma (por exemplo, "1.000" que virou "mil").

Usa só a biblioteca padrão. As fontes precisam estar em texto (.md, .txt). Para
PDF ou DOCX, salve antes o texto extraído em um arquivo e passe esse arquivo.

Código de saída: 0 quando não há nada a conferir, 1 quando há.
"""
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

SECTIONS = [
    "1. Contexto e Motivação",
    "2. Fundamentos e Conceitos-Chave",
    "3. Panorama e Abordagens Existentes",
    "4. Arquiteturas e Modelos de Aplicação",
    "5. Estratégias, Algoritmos e Mecanismos",
    "6. Tecnologias, Frameworks e Ferramentas",
    "7. Boas Práticas e Diretrizes Técnicas",
    "8. Métricas e Critérios de Avaliação",
    "9. Casos de Uso e Aplicações Reais",
    "10. Riscos, Desafios e Limitações",
    "11. Considerações de Segurança, Confiabilidade e Governança",
    "12. Tendências e Evolução Futura",
    "13. Impactos e Relações com o Ecossistema",
    "14. Decisões e Oportunidades Técnicas (ADRs Candidatos)",
    "15. Próximos Passos e Aplicação Prática",
    "16. Referências e Leituras Recomendadas",
]
HEADER_FIELDS = ["**Título:**", "**Versão:**", "**Data:**", "**Responsável:**"]

# Trechos das descrições do esqueleto. Se aparecerem no documento, o texto-guia
# do modelo foi copiado em vez de substituído pelo conteúdo.
SKELETON_GUIDES = [
    "Descreve o problema técnico, a oportunidade ou a motivação",
    "Apresenta princípios, teorias, modelos ou terminologias",
    "Analisa as abordagens predominantes, soluções conhecidas",
    "Explica como o tema é aplicado em nível arquitetural",
    "Lista as principais estratégias, algoritmos e mecanismos",
    "Apresenta tecnologias, bibliotecas, protocolos ou frameworks relevantes",
    "Inclui recomendações de implementação, anti-patterns",
    "Define como mensurar o sucesso técnico ou operacional",
    "Mostra exemplos de aplicação prática, estudos de caso",
    "Descreve riscos, limitações técnicas, pontos de falha",
    "Trata de aspectos de segurança, conformidade, privacidade",
    "Apresenta tendências, inovações ou pesquisas emergentes",
    "Explica como o tema interage com outros sistemas",
    "Lista possíveis decisões técnicas ou arquiteturais derivadas",
    "Propõe como aplicar os aprendizados em produtos",
    "Apresenta todas as fontes utilizadas",
]

FORBIDDEN = [
    (re.compile(r"\bp[áa]gina\s+\d+", re.I), "divisão ou marcação de página"),
    (
        re.compile(
            r"\b(documento|arquivo|material|conte[úu]do|texto)\s+"
            r"(anexad[oa]|importad[oa]|fornecid[oa]|de origem)\b",
            re.I,
        ),
        "referência ao material de origem",
    ),
    (re.compile(r"\b(no|do|conforme o|segundo o|veja o)\s+(anexo|pdf)\b", re.I), "referência ao material de origem"),
    (re.compile(r"|||cite(turn\d+\w*)+", re.I), "marcador interno de citação da ferramenta"),
    (re.compile(r"【[^】]*】"), "marcador interno de citação da ferramenta"),
    (re.compile(r"\[cite(?:_start|_end)?[^\]]*\]|:contentReference\[", re.I), "marcador interno de citação da ferramenta"),
]

URL_RE = re.compile(r"https?://[^\s<>\"'`)\]]+")
FENCE_RE = re.compile(r"^(`{3,}|~{3,})[^\n]*\n(.*?)^\1[ \t]*$", re.S | re.M)
INLINE_CODE_RE = re.compile(r"`([^`\n]{2,})`")
NUM_RE = re.compile(r"(?<![\w.,/-])(\d+(?:[.,]\d+)*)(?![\w])")
TOKEN_RE = re.compile(r"(?<![\w])([A-Za-z][\w.+#/-]*[A-Za-z0-9+#]|[A-Za-z])")
WORD_RE = re.compile(r"\w+", re.UNICODE)
MAX_LISTED = 200


def read(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    return unicodedata.normalize("NFC", text)


def squash(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def split_code(text: str) -> tuple[str, list[str]]:
    """Separa os blocos de código do texto corrido."""
    blocks = [m.group(2) for m in FENCE_RE.finditer(text)]
    return FENCE_RE.sub(" ", text), blocks


def clean_url(url: str) -> str:
    return url.rstrip(".,;:!?")


def number_variants(num: str) -> set[str]:
    swapped = num.translate(str.maketrans({".": ",", ",": "."}))
    return {num, swapped, num.replace(".", "").replace(",", "")}


def is_technical_term(token: str) -> bool:
    # Siglas (API, HTTP/2) e nomes com maiúscula no meio (PostgreSQL, gRPC).
    # Palavras com só a inicial maiúscula ficam de fora: geram ruído demais.
    return len(token) >= 2 and any(c.isupper() for c in token[1:])


def context(text: str, needle: str, width: int = 50) -> str:
    pos = text.find(needle)
    if pos < 0:
        pos = text.lower().find(needle.lower())
    if pos < 0:
        return ""
    start, end = max(0, pos - width), min(len(text), pos + len(needle) + width)
    return squash(text[start:end])


def unique(items):
    seen, out = set(), []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def check_structure(doc: str) -> list[str]:
    problems = []
    lines = [line.rstrip() for line in doc.splitlines()]
    if "# Deep Research Document" not in lines:
        problems.append('falta o título "# Deep Research Document"')
    for field in HEADER_FIELDS:
        if not any(line.startswith(field) for line in lines):
            problems.append(f"falta o campo de cabeçalho {field}")

    found = [line[3:].strip() for line in lines if line.startswith("## ")]
    positions = []
    for name in SECTIONS:
        if name in found:
            positions.append(found.index(name))
        else:
            near = [h for h in found if h.split(" ", 1)[0] == name.split(" ", 1)[0]]
            hint = f' (encontrado: "## {near[0]}")' if near else ""
            problems.append(f'seção ausente ou com nome diferente: "## {name}"{hint}')
    if positions != sorted(positions):
        problems.append("as seções não estão na ordem do esqueleto")
    extra = [h for h in found if h not in SECTIONS]
    for h in extra:
        problems.append(f'título de nível 2 fora do esqueleto: "## {h}" (use ### para subseções)')

    for guide in SKELETON_GUIDES:
        if guide in doc:
            problems.append(f'texto-guia do esqueleto copiado: "{guide}..."')
    hits: dict[tuple[str, str], list[int]] = {}
    for regex, label in FORBIDDEN:
        for m in regex.finditer(doc):
            key = (label, m.group(0).lower())
            if key not in hits:
                hits[key] = [doc.count("\n", 0, m.start()) + 1, 0]
            hits[key][1] += 1
    for (label, text), (line_no, count) in hits.items():
        extra = f", {count} ocorrências" if count > 1 else ""
        problems.append(f'{label}: "{text}" (primeira na linha {line_no}{extra})')
    return problems


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", required=True, type=Path, help="Deep Research Document gerado (.md)")
    parser.add_argument("--source", required=True, type=Path, action="append", help="material de origem em texto; repita para vários")
    args = parser.parse_args()

    doc = read(args.output)
    source = "\n\n".join(read(p) for p in args.source)

    src_text, src_code = split_code(source)
    doc_text, doc_code = split_code(doc)
    doc_squashed = squash(doc)

    # URLs
    doc_urls = {clean_url(u) for u in URL_RE.findall(doc)}
    missing_urls = [u for u in unique(clean_url(u) for u in URL_RE.findall(source)) if u not in doc_urls]

    # Números (fora de URLs e de código); inteiros de um dígito não são conferidos.
    src_plain = URL_RE.sub(" ", src_text)
    doc_plain = URL_RE.sub(" ", doc_text)
    doc_numbers = set()
    for n in NUM_RE.findall(doc_plain):
        doc_numbers |= number_variants(n)
    missing_numbers = [
        n for n in unique(NUM_RE.findall(src_plain))
        if len(n.replace(".", "").replace(",", "")) >= 2 and not (number_variants(n) & doc_numbers)
    ]

    # Termos técnicos
    doc_tokens = {t.lower() for t in TOKEN_RE.findall(doc_plain)}
    missing_terms = [
        t for t in unique(TOKEN_RE.findall(src_plain))
        if is_technical_term(t) and t.lower() not in doc_tokens
    ]

    # Código
    missing_inline = [c for c in unique(INLINE_CODE_RE.findall(src_text)) if c not in doc]
    missing_blocks = [b for b in src_code if squash(b) and squash(b) not in doc_squashed]

    structure = check_structure(doc)

    src_words = len(WORD_RE.findall(source))
    doc_words = len(WORD_RE.findall(doc))
    ratio = doc_words / src_words if src_words else 0.0

    print("Verificação de cobertura do Deep Research Document")
    print(f"Documento: {args.output}")
    print("Origem: " + ", ".join(str(p) for p in args.source))
    print(f"Palavras: origem {src_words}, documento {doc_words} ({ratio:.0%})")
    if ratio < 0.9:
        print("  ATENÇÃO: o documento tem menos palavras que a origem. Reorganizar sem resumir")
        print("  normalmente mantém ou aumenta o tamanho; procure trechos condensados ou omitidos.")
    print()

    total = 0

    def report(title: str, items: list[str], show_context: bool = True) -> None:
        nonlocal total
        total += len(items)
        print(f"{title}: {len(items)}")
        for item in items[:MAX_LISTED]:
            line = squash(item)
            if len(line) > 120:
                line = line[:117] + "..."
            ctx = context(source, item) if show_context else ""
            print(f"  - {line}" + (f'\n      origem: "...{ctx}..."' if ctx and ctx != line else ""))
        if len(items) > MAX_LISTED:
            print(f"  ... e mais {len(items) - MAX_LISTED}")
        print()

    report("Problemas de estrutura", structure, show_context=False)
    report("URLs ausentes", missing_urls)
    report("Números ausentes", missing_numbers)
    report("Termos técnicos ausentes", missing_terms)
    report("Código inline ausente", missing_inline)
    report("Blocos de código ausentes", missing_blocks, show_context=False)

    if total:
        print(f"Resultado: {total} item(ns) para conferir.")
        return 1
    print("Resultado: nenhuma ausência detectada nos itens objetivos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
