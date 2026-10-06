"""
Auditoria de completude do catalogo (Drive) - IL Variedades Enxovais

O QUE ESTE SCRIPT FAZ
----------------------
Varre a mesma estrutura do Drive que conectar_drive.py conhece (produtos/
categoria/produto/estampas|fotos variadas|produto no ambiente|descricao) e
gera um indice local (catalogo_completude.json) com quantas fotos cada
produto tem em cada subpasta.

PRA QUE SERVE
-------------
Esse indice existe pra responder perguntas como "quais produtos ainda nao
tem foto em 'fotos variadas'?" sem precisar escanear o Drive inteiro toda
vez -- foi exatamente isso que foi feito na mao, em varias rodadas, durante
o desenvolvimento do projeto (reunir estampas/fotos variadas/produto no
ambiente por produto). Esse script automatiza aquele processo.

Uso pretendido: rodar antes de qualquer validacao que precise saber "esse
produto tem material suficiente pra gerar conteudo?" -- por exemplo, a
verificacao de divergencia do app descrito no planejamento ("produto
selecionado que nao tem as estampas"). Em vez de escanear o Drive ao vivo
a cada comando, consulta esse JSON (e roda esse script de novo soh quando
o catalogo mudar, nao a cada postagem).

COMO RODAR
----------
python auditar_catalogo.py                 # gera catalogo_completude.json e imprime resumo
python auditar_catalogo.py --so-incompletos # imprime so os produtos com pendencia
"""

import argparse
import json
from pathlib import Path

from conectar_drive import ID_PASTA_PRODUTOS, conectar, listar_imagens, listar_subpastas

ARQUIVO_SAIDA = "catalogo_completude.json"

SUBPASTAS_RELEVANTES = ["estampas", "fotos variadas", "produto no ambiente", "descrição"]


def _contar_imagens(servico, id_subpasta: str | None) -> int:
    if not id_subpasta:
        return 0
    return len(listar_imagens(servico, id_subpasta))


def auditar() -> dict:
    servico = conectar()
    produtos = []

    categorias = listar_subpastas(servico, ID_PASTA_PRODUTOS)
    print(f"Encontradas {len(categorias)} categorias no Drive.\n")

    for id_categoria, nome_categoria in categorias:
        produtos_da_categoria = listar_subpastas(servico, id_categoria)
        print(f"[{nome_categoria}] {len(produtos_da_categoria)} produtos")

        for id_produto, nome_produto in produtos_da_categoria:
            subpastas = {nome: id_ for id_, nome in listar_subpastas(servico, id_produto)}

            contagens = {
                chave: _contar_imagens(servico, subpastas.get(chave))
                for chave in SUBPASTAS_RELEVANTES
                if chave != "descrição"
            }
            tem_descricao = bool(subpastas.get("descrição"))
            tem_estrutura = bool(subpastas)  # produto pode ainda nao ter nenhuma das 4 subpastas

            produtos.append({
                "categoria": nome_categoria,
                "nome": nome_produto,
                "tem_estrutura_de_pastas": tem_estrutura,
                "estampas": contagens.get("estampas", 0),
                "fotos_variadas": contagens.get("fotos variadas", 0),
                "produto_no_ambiente": contagens.get("produto no ambiente", 0),
                "tem_descricao": tem_descricao,
            })

    return {"produtos": produtos}


def resumir(catalogo: dict, so_incompletos: bool = False) -> None:
    produtos = catalogo["produtos"]
    total = len(produtos)
    sem_nada = [p for p in produtos if p["estampas"] == 0 and p["fotos_variadas"] == 0]
    so_falta_variadas = [
        p for p in produtos if p["estampas"] > 0 and p["fotos_variadas"] == 0
    ]
    sem_ambiente = [p for p in produtos if p["produto_no_ambiente"] == 0]

    print(f"\n{'=' * 60}")
    print(f"Total de produtos: {total}")
    print(f"Sem nenhuma foto (nem estampas, nem fotos variadas): {len(sem_nada)}")
    print(f"Falta so 'fotos variadas' (estampas ok): {len(so_falta_variadas)}")
    print(f"Sem 'produto no ambiente': {len(sem_ambiente)}")
    print(f"{'=' * 60}\n")

    if not so_incompletos:
        return

    if sem_nada:
        print("--- SEM NENHUMA FOTO ---")
        for p in sem_nada:
            print(f"  [{p['categoria']}] {p['nome']}")
    if so_falta_variadas:
        print("\n--- FALTA 'FOTOS VARIADAS' ---")
        for p in so_falta_variadas:
            print(f"  [{p['categoria']}] {p['nome']}")
    if sem_ambiente:
        print("\n--- SEM 'PRODUTO NO AMBIENTE' ---")
        for p in sem_ambiente:
            print(f"  [{p['categoria']}] {p['nome']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--so-incompletos", action="store_true",
        help="Imprime a lista detalhada de produtos com pendencia (alem do resumo)",
    )
    args = parser.parse_args()

    catalogo = auditar()

    with open(ARQUIVO_SAIDA, "w", encoding="utf-8") as f:
        json.dump(catalogo, f, ensure_ascii=False, indent=2)

    print(f"\nIndice salvo em {ARQUIVO_SAIDA}")
    resumir(catalogo, so_incompletos=args.so_incompletos)
