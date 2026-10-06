"""
Enriquecimento de cor_predominante - IL Variedades Enxovais

O QUE ESTE SCRIPT FAZ
----------------------
produtos_reais.json tem um campo "cor_predominante" que o
conectar_drive.py nunca preenche (fica sempre ""). Sem ele,
gerar_carrossel_completo._construir_paleta_em_foco (formato do padrao
"estilo_vida") usa a CATEGORIA do produto como se fosse cor, o que nao
faz sentido nenhum (ex: mostrar "cama (quarto)" como rotulo de paleta).

Esse script roda 1x (ou sempre que entrar produto novo sem cor) e pede
pro Gemini olhar a foto real do produto (imagem_ambiente, ou
imagem_estampa se nao tiver a primeira) e classificar a cor
predominante do TECIDO/PRODUTO numa lista fixa de opcoes -- ignorando o
cenario/ambiente ao redor. Grava o resultado direto em
produtos_reais.json.

COMO RODAR
----------
1. Rode conectar_drive.py primeiro (precisa das fotos em banco_local/
   e dos campos imagem_ambiente/imagem_estampa preenchidos)
2. export GEMINI_API_KEY="sua_chave_aqui"
3. python enriquecer_cores.py

Por padrao SO preenche produtos com cor_predominante vazio (nao gasta
chamada de API de novo em produto ja classificado). Use --forcar pra
reclassificar todos.
"""

import argparse
import json

from gerar_carrossel_gemini import _carregar_bytes_imagem, _obter_cliente, _part_de_bytes, MODELO_IMAGEM

ARQUIVO_BANCO = "produtos_reais.json"

CORES_VALIDAS = [
    "branco", "bege", "cinza", "preto", "azul", "verde",
    "rosa", "vermelho", "amarelo", "marrom", "lilás", "estampado",
]


def _montar_prompt() -> str:
    opcoes = ", ".join(CORES_VALIDAS)
    return (
        "Olhe so para o PRODUTO TEXTIL na foto (colcha, lencol, toalha, "
        "tapete, cortina, etc.) -- ignore o fundo/ambiente/moveis ao "
        "redor. Qual e a cor predominante do tecido?\n\n"
        f"Responda com UMA PALAVRA SO, exatamente uma destas opcoes: {opcoes}.\n"
        "Se o produto tiver varias cores bem misturadas, sem nenhuma "
        "clara predominancia (ex: estampa floral colorida, xadrez "
        "multicolor), responda 'estampado'.\n"
        "Nao escreva mais nada alem da palavra escolhida."
    )


def inferir_cor_predominante(produto: dict) -> str | None:
    referencia = produto.get("imagem_ambiente") or produto.get("imagem_estampa")
    if not referencia:
        return None

    client = _obter_cliente()
    dados, mime_type = _carregar_bytes_imagem(referencia)
    partes = [_part_de_bytes(dados, mime_type), _montar_prompt()]

    resposta = client.models.generate_content(model=MODELO_IMAGEM, contents=partes)
    cor = (resposta.text or "").strip().lower()
    cor = cor.strip(".").split()[0] if cor else ""
    return cor if cor in CORES_VALIDAS else None


def rodar(forcar: bool = False) -> None:
    with open(ARQUIVO_BANCO, encoding="utf-8") as f:
        banco = json.load(f)

    produtos = banco["produtos"]
    alvo = produtos if forcar else [p for p in produtos if not p.get("cor_predominante")]
    print(f"{len(alvo)}/{len(produtos)} produtos para classificar.\n")

    classificados = 0
    for produto in alvo:
        print(f"[{produto['id']}] {produto['nome']}...", end=" ")
        try:
            cor = inferir_cor_predominante(produto)
        except Exception as erro:
            print(f"erro: {erro}")
            continue

        if cor:
            produto["cor_predominante"] = cor
            classificados += 1
            print(cor)
        else:
            print("sem foto de referencia ou resposta invalida, pulado")

    with open(ARQUIVO_BANCO, "w", encoding="utf-8") as f:
        json.dump(banco, f, ensure_ascii=False, indent=2)

    print(f"\nConcluido! {classificados} produto(s) classificado(s) e salvos em {ARQUIVO_BANCO}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--forcar", action="store_true",
        help="Reclassifica mesmo produtos que ja tem cor_predominante preenchido"
    )
    args = parser.parse_args()
    rodar(forcar=args.forcar)
