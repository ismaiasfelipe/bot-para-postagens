"""
Orquestrador semanal - IL Variedades Enxovais

O QUE ESTE SCRIPT FAZ
----------------------
Roda o pipeline inteiro uma vez:
1. Descobre a campanha ativa na semana (calendario_campanhas.py) ou usa
   o fluxo generico se nenhuma estiver ativa
2. Escolhe um produto que combine com a campanha (categoria) e que nao
   tenha sido usado nos ultimos 8 posts (historico_publicacoes.json)
3. Escolhe o formato de carrossel (o sugerido pela campanha, ou um dos
   genericos em rodizio)
4. Gera a foto "hero" do produto via Gemini -- REAPROVEITA se ja existir
   saida/{produto_id}_0.png (evita custo/gasto repetido)
5. Monta os 4 slides do carrossel (gerar_carrossel_completo.py)
6. Escreve a legenda no tom de voz da campanha (ou generico)
7. Se publicar=True: sobe pro storage e publica de verdade no Instagram,
   e registra no historico

ESCOPO ATUAL -- IMPORTANTE
----------------------------
So usa os 5 formatos que precisam de 1 unica foto hero: vitrine,
campanha_sazonal, promocao_relampago, novidade_semana, detalhe_textura.
Os outros 5 formatos (kit_combo, inspiracao_decoracao, giro_categoria,
paleta_em_foco, ambientes_estilos) exigem multiplas fotos/produtos por
slide e ainda pedem curadoria manual -- nao estao no rodizio automatico.

CUSTO E EFEITOS
------------------
- Gerar uma foto nova (quando o produto ainda nao tem saida/{id}_0.png)
  chama a API do Gemini -- tem custo. Mesmo com publicar=False isso pode
  acontecer, porque a foto e necessaria pra montar o preview do carrossel.
- publicar=True sobe imagens pro Google Cloud Storage e publica um post
  DE VERDADE no Instagram real da loja. So rode assim com confirmacao.

COMO RODAR
----------
python executar_pipeline_semanal.py            # so mostra o que faria (nao publica)
python executar_pipeline_semanal.py --publicar  # publica de verdade
"""

import argparse
import json
from datetime import date
from pathlib import Path

from calendario_campanhas import CAMPANHAS, campanhas_ativas_na_semana, montar_legenda, HASHTAGS_FIXAS
from tema_semana import carregar_tema
from gerar_carrossel_gemini import gerar_foto_hero_com_verificacao
from gerar_carrossel_completo import gerar_carrossel
from upload_storage import enviar_carrossel
from publicar_instagram import publicar_carrossel

ARQUIVO_PRODUTOS = "produtos_reais.json"
ARQUIVO_HISTORICO = "historico_publicacoes.json"
FORMATOS_SIMPLES_GENERICOS = ["vitrine", "novidade_semana", "detalhe_textura"]


def _carregar_produtos() -> list[dict]:
    with open(ARQUIVO_PRODUTOS, encoding="utf-8") as f:
        return json.load(f)["produtos"]


def _carregar_historico() -> list[dict]:
    if not Path(ARQUIVO_HISTORICO).exists():
        return []
    with open(ARQUIVO_HISTORICO, encoding="utf-8") as f:
        return json.load(f)


def _salvar_historico(historico: list[dict]) -> None:
    with open(ARQUIVO_HISTORICO, "w", encoding="utf-8") as f:
        json.dump(historico, f, ensure_ascii=False, indent=2)


def _categoria_bate(categoria_produto: str, categoria_campanha: str) -> bool:
    if categoria_campanha == "Todas":
        return True
    return categoria_produto.lower().startswith(categoria_campanha.lower())


def _campanha_sintetica_categoria(categoria: str) -> dict:
    """Tema da semana com so categoria (sem campanha do calendario) -- ver tema_semana.py."""
    return {
        "chave": f"foco_{categoria.lower()}",
        "nome": f"Semana de {categoria}",
        "categorias": [categoria],
        "cta": "Chame no direct e garanta o seu!",
        "hashtags_extras": "",
        "tom_detalhe": "",
        "combina_com": "",
        "formato_sugerido": "vitrine",
    }


def escolher_campanha() -> dict | None:
    """
    Prioridade: tema da semana definido manualmente (tema_semana.py) >
    campanha ativa pelo calendario > nenhuma (fluxo generico).
    """
    tema = carregar_tema()
    if tema:
        if tema.get("campanha_chave"):
            encontrada = next((c for c in CAMPANHAS if c["chave"] == tema["campanha_chave"]), None)
            if encontrada:
                return encontrada
        if tema.get("categoria_foco"):
            return _campanha_sintetica_categoria(tema["categoria_foco"])

    ativas = campanhas_ativas_na_semana()
    return ativas[0] if ativas else None


def escolher_produtos_candidatos(campanha: dict | None, historico: list[dict]) -> list[dict]:
    """
    Devolve os produtos candidatos em ordem de preferencia (nao usados
    recentemente primeiro). Devolve uma LISTA -- se o primeiro candidato
    reprovar na verificacao de foto (obter_foto_hero), o chamador tenta o
    proximo em vez de travar ou publicar algo errado.

    Se o tema da semana forcar um produto especifico (tema_semana.py),
    devolve so ele -- sem rodizio.
    """
    tema = carregar_tema()
    produtos = _carregar_produtos()

    if tema and tema.get("produto_id"):
        forcado = next((p for p in produtos if p["id"] == tema["produto_id"]), None)
        if forcado:
            return [forcado]

    usados_recentes = {h["produto_id"] for h in historico[-8:]}

    candidatos = produtos
    if campanha:
        filtrados = [
            p for p in produtos
            if any(_categoria_bate(p["categoria"], c) for c in campanha["categorias"])
        ]
        if filtrados:
            candidatos = filtrados

    nao_usados = [p for p in candidatos if p["id"] not in usados_recentes]
    usados = [p for p in candidatos if p["id"] in usados_recentes]
    return nao_usados + usados  # nao usados primeiro, usados como ultimo recurso


def escolher_formato(campanha: dict | None, historico: list[dict]) -> str:
    if campanha:
        return campanha.get("formato_sugerido", "vitrine")
    n = len(historico)
    return FORMATOS_SIMPLES_GENERICOS[n % len(FORMATOS_SIMPLES_GENERICOS)]


def obter_foto_hero(produto: dict) -> str | None:
    """
    Reaproveita uma foto ja verificada em cache/hero/{id}.png se existir;
    senao gera uma nova via Gemini COM verificacao automatica de
    fidelidade (gerar_foto_hero_com_verificacao, com retry) e salva no
    cache so se aprovada.

    Retorna None se reprovar em todas as tentativas -- o chamador deve
    pular esse produto, nunca publicar uma foto reprovada.

    Cache separado de saida/ de proposito: os arquivos soltos em saida/
    (de sessoes anteriores a 03/09/2026) nao passaram por verificacao e
    alguns saem com cenas genericas sem relacao com o produto real (ver
    PROJETO.md, "Verificacao de foto hero") -- so o cache novo, com
    aprovacao confirmada, e reaproveitado automaticamente.
    """
    pasta_cache = Path("cache_hero")
    pasta_cache.mkdir(exist_ok=True)
    caminho_cache = pasta_cache / f"{produto['id']}.png"
    if caminho_cache.exists():
        return str(caminho_cache)

    aprovado = gerar_foto_hero_com_verificacao(produto)
    if aprovado is None:
        return None

    caminho_cache.write_bytes(Path(aprovado).read_bytes())
    return str(caminho_cache)


def montar_dados_formato(formato: str, campanha: dict | None, foto_hero: str) -> dict:
    if formato == "campanha_sazonal":
        return {
            "foto_principal": foto_hero,
            "campanha": {
                "nome": campanha["nome"],
                "cta": campanha["cta"],
                "hashtags": f"{campanha['hashtags_extras']} {HASHTAGS_FIXAS}",
                "combina_com": campanha.get("combina_com", ""),
                "tom_detalhe": campanha.get("tom_detalhe", ""),
            },
        }
    if formato == "promocao_relampago":
        # "condicao" vira o titulo grande do slide 3 (montar_post) -- tem
        # que ser curto, NUNCA a frase inteira do CTA (que ja aparece,
        # por completo, no slide 4), senao o texto estoura o slide. O
        # nome/data da campanha ja aparecem nos slides 1 e 2, nao repete.
        return {
            "foto_principal": foto_hero,
            "data_promocao": date.today().strftime("%d/%m"),
            "condicao": "Condição especial, só hoje!",
        }
    return {"foto_principal": foto_hero}  # vitrine, novidade_semana, detalhe_textura


def rodar(publicar: bool = False) -> None:
    campanha = escolher_campanha()
    historico = _carregar_historico()
    candidatos = escolher_produtos_candidatos(campanha, historico)
    formato = escolher_formato(campanha, historico)

    print(f"Campanha ativa: {campanha['nome'] if campanha else 'nenhuma (fluxo generico)'}")
    print(f"Formato: {formato}")

    produto = None
    foto_hero = None
    for candidato in candidatos:
        print(f"\nTentando produto: {candidato['id']} - {candidato['nome']}")
        foto_hero = obter_foto_hero(candidato)
        if foto_hero is not None:
            produto = candidato
            break
        print(f"  '{candidato['id']}' reprovado na verificacao, tentando o proximo candidato...")

    if produto is None:
        print("\nNenhum produto candidato passou na verificacao de foto. Nada foi publicado.")
        return

    print(f"\nProduto escolhido: {produto['id']} - {produto['nome']}")
    print(f"Foto hero: {foto_hero}")

    dados_formato = montar_dados_formato(formato, campanha, foto_hero)
    slides = gerar_carrossel(formato, produto["id"], **dados_formato)
    print(f"Slides montados: {slides}")

    legenda = montar_legenda(campanha, produto["nome"])
    print(f"\nLegenda:\n{legenda}\n")

    if not publicar:
        print("Modo preview (sem --publicar) -- nada foi enviado pro storage nem publicado.")
        return

    urls = enviar_carrossel(slides)
    post_id = publicar_carrossel(urls, legenda)
    print(f"Publicado com sucesso! ID do post: {post_id}")

    historico.append({
        "data": date.today().isoformat(),
        "produto_id": produto["id"],
        "campanha": campanha["chave"] if campanha else None,
        "formato": formato,
        "post_id": post_id,
    })
    _salvar_historico(historico)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--publicar", action="store_true", help="Publica de verdade no Instagram")
    args = parser.parse_args()
    rodar(publicar=args.publicar)
