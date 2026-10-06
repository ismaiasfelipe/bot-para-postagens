"""
Metricas de performance (insights) - IL Variedades Enxovais

O QUE ESTE SCRIPT FAZ
----------------------
Busca as metricas reais de cada post/story ja publicado (alcance,
curtidas, comentarios, etc.) na API do Instagram e atualiza
historico_publicacoes.json com elas -- ate agora o historico so guardava
o ID do post/story, sem nenhum dado de performance (ver item 3 do
planejamento, "relatorio").

Rode isso periodicamente (ver .github/workflows/atualizar_metricas.yml,
diario) pra manter o relatorio atualizado -- nao roda sozinho junto do
pipeline de publicacao porque a metrica de um post so fica interessante
depois de ter circulado um tempo, nao no momento exato da publicacao.

LIMITACOES CONHECIDAS DA API (Instagram Graph API via Instagram Login)
--------------------------------------------------------------------------
- Stories: as metricas somem depois que o story expira (24h). Rodar esse
  script com frequencia (diario) e essencial pra capturar o numero antes
  de expirar -- depois disso a chamada falha e o story fica sem metrica
  pra sempre (normal, nao e bug).
- Os nomes exatos de metrica mudam de vez em quando entre versoes da
  API (ex: "impressions" foi descontinuada pra posts novos em versoes
  recentes, substituida por "views"). Se a lista METRICAS_POST/
  METRICAS_STORY abaixo comecar a dar erro 400, confira a versao atual
  em https://developers.facebook.com/docs/instagram-platform/insights
  e ajuste -- esse script tenta cada metrica individualmente e ignora
  so a que falhar, em vez de travar tudo.

COMO RODAR
----------
python relatorio_instagram.py
"""

import json
import time
from pathlib import Path

import requests

from publicar_instagram import GRAPH_BASE, IG_ACCESS_TOKEN, _checar_credenciais

ARQUIVO_HISTORICO = "historico_publicacoes.json"

METRICAS_POST = ["reach", "likes", "comments", "saved", "shares", "total_interactions"]
METRICAS_STORY = ["reach", "replies", "navigation"]


def _carregar_historico() -> list[dict]:
    if not Path(ARQUIVO_HISTORICO).exists():
        return []
    with open(ARQUIVO_HISTORICO, encoding="utf-8") as f:
        return json.load(f)


def _salvar_historico(historico: list[dict]) -> None:
    with open(ARQUIVO_HISTORICO, "w", encoding="utf-8") as f:
        json.dump(historico, f, ensure_ascii=False, indent=2)


def _buscar_metricas(media_id: str, metricas: list[str]) -> dict:
    """
    Busca cada metrica INDIVIDUALMENTE (nao numa chamada so com todas
    separadas por virgula) pra uma metrica invalida/indisponivel nao
    derrubar as outras -- a API rejeita a chamada inteira se UMA metrica
    da lista nao for suportada pro tipo de midia.
    """
    resultado = {}
    for metrica in metricas:
        resposta = requests.get(
            f"{GRAPH_BASE}/{media_id}/insights",
            params={"metric": metrica, "access_token": IG_ACCESS_TOKEN},
        )
        dados = resposta.json()
        if resposta.status_code != 200:
            continue  # metrica indisponivel pra essa midia/versao da API -- ignora so essa
        valores = dados.get("data", [])
        if valores and valores[0].get("values"):
            resultado[metrica] = valores[0]["values"][0].get("value")
    return resultado


def obter_metricas_post(post_id: str) -> dict:
    """Metricas de um carrossel/imagem publicado (ver METRICAS_POST)."""
    return _buscar_metricas(post_id, METRICAS_POST)


def obter_metricas_story(story_id: str) -> dict:
    """
    Metricas de um story publicado (ver METRICAS_STORY). Retorna {} se o
    story ja expirou (24h) -- a API nao da mais detalhe do motivo, so
    passa a rejeitar a chamada.
    """
    return _buscar_metricas(story_id, METRICAS_STORY)


def atualizar_metricas_historico(dias_recentes: int = 7) -> None:
    """
    Atualiza as metricas de todo post/story publicado nos ultimos
    'dias_recentes' dias (por padrao, so a ultima semana -- posts mais
    antigos ja estabilizaram e stories mais antigos ja expiraram havia
    tempo, nao vale a pena gastar chamada de API neles de novo).

    Salva em cada entrada do historico:
      "metricas": {...}                          (do post/carrossel)
      "metricas_stories": {"<story_id>": {...}}  (por story)
      "metricas_atualizadas_em": "AAAA-MM-DD"
    """
    _checar_credenciais()
    historico = _carregar_historico()
    if not historico:
        print("Historico vazio, nada pra atualizar.")
        return

    from datetime import date, timedelta
    limite = (date.today() - timedelta(days=dias_recentes)).isoformat()

    atualizados = 0
    for entrada in historico:
        if entrada.get("data", "") < limite:
            continue

        post_id = entrada.get("post_id")
        if post_id:
            print(f"  buscando metricas do post {post_id} ({entrada.get('produto_id')})...")
            metricas = obter_metricas_post(post_id)
            if metricas:
                entrada["metricas"] = metricas
                atualizados += 1
            time.sleep(1)  # evita bater no limite de taxa da API

        story_ids = entrada.get("story_ids") or []
        if story_ids:
            metricas_stories = entrada.get("metricas_stories", {})
            for story_id in story_ids:
                print(f"  buscando metricas do story {story_id}...")
                metricas = obter_metricas_story(story_id)
                if metricas:
                    metricas_stories[story_id] = metricas
                    atualizados += 1
                time.sleep(1)
            if metricas_stories:
                entrada["metricas_stories"] = metricas_stories

        if post_id or story_ids:
            entrada["metricas_atualizadas_em"] = date.today().isoformat()

    _salvar_historico(historico)
    print(f"\nConcluido. {atualizados} post(s)/story(ies) com metricas atualizadas.")


if __name__ == "__main__":
    atualizar_metricas_historico()
