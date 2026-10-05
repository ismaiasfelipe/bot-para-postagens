"""
Publicacao automatica no Instagram - IL Variedades Enxovais

O QUE ESTE SCRIPT FAZ
Usa a API do Instagram (login direto da conta Business, sem passar por
Pagina do Facebook) para:
1. Verificar se o token de acesso em .env esta valido (testar_conexao)
2. Trocar um token de curta duracao por um de longa duracao, ~60 dias
   (trocar_por_token_longa_duracao) -- o token gerado no painel do Meta
   for Developers normalmente ja vem de curta duracao (1h)
3. Publicar um carrossel (2 a 10 imagens) a partir de URLs publicas
   (publicar_carrossel) -- a API do Instagram so aceita imagem via URL
   publica, nao upload direto de arquivo. Use upload_storage.py pra
   subir os slides gerados e obter essas URLs antes de chamar isso.
4. Publicar uma imagem unica (publicar_imagem_unica)
5. Publicar um Story (publicar_story) -- mesmo fluxo de container da
   imagem unica, so troca media_type pra "STORIES". Sem app review
   adicional: a permissao instagram_content_publish que ja libera
   carrossel/imagem cobre Stories tambem. Duas limitacoes da API (nao
   tem solucao via codigo):
   - Nao renderiza "caption" em Stories -- todo texto tem que estar
     desenhado na propria imagem antes de publicar.
   - Nao da pra inserir sticker nativo (enquete, caixinha de pergunta)
     por essa API -- isso so da pra fazer manualmente, direto no app.

Fluxo interno de publicacao de carrossel (exigido pela API):
1. Criar um "media container" pra cada imagem (is_carousel_item=true)
2. Criar um "media container" do tipo CAROUSEL referenciando os itens
3. Publicar o container do carrossel (media_publish)
Cada etapa tem que aguardar o container ficar pronto (status_code
FINISHED) antes de seguir pra proxima -- ver _aguardar_container_pronto.
"""

import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

GRAPH_API_VERSION = "v22.0"
GRAPH_BASE = f"https://graph.instagram.com/{GRAPH_API_VERSION}"

IG_USER_ID = os.getenv("IG_USER_ID")
IG_ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN")
IG_APP_ID = os.getenv("IG_APP_ID")
IG_APP_SECRET = os.getenv("IG_APP_SECRET")


def _checar_credenciais():
    faltando = [
        nome
        for nome, valor in [
            ("IG_USER_ID", IG_USER_ID),
            ("IG_ACCESS_TOKEN", IG_ACCESS_TOKEN),
        ]
        if not valor
    ]
    if faltando:
        raise RuntimeError(
            f"Faltam variaveis no .env: {', '.join(faltando)}. "
            "Veja o arquivo .env na raiz do projeto."
        )


def testar_conexao():
    """Confirma que o token funciona, buscando dados basicos da conta."""
    _checar_credenciais()
    resp = requests.get(
        f"{GRAPH_BASE}/{IG_USER_ID}",
        params={
            "fields": "id,username,account_type,media_count",
            "access_token": IG_ACCESS_TOKEN,
        },
    )
    dados = resp.json()
    if resp.status_code != 200:
        raise RuntimeError(f"Erro ao conectar na API do Instagram: {dados}")
    return dados


def trocar_por_token_longa_duracao(token_curta_duracao=None):
    """
    Troca um token de curta duracao (1h) por um de longa duracao (~60 dias).
    Retorna o novo token -- salve manualmente em IG_ACCESS_TOKEN no .env
    depois de rodar isso.
    """
    token = token_curta_duracao or IG_ACCESS_TOKEN
    if not IG_APP_SECRET:
        raise RuntimeError("IG_APP_SECRET nao configurado no .env")
    resp = requests.get(
        "https://graph.instagram.com/access_token",
        params={
            "grant_type": "ig_exchange_token",
            "client_secret": IG_APP_SECRET,
            "access_token": token,
        },
    )
    dados = resp.json()
    if resp.status_code != 200:
        raise RuntimeError(f"Erro ao trocar token: {dados}")
    return dados  # {"access_token": "...", "token_type": "bearer", "expires_in": segundos}


def _aguardar_container_pronto(container_id, max_tentativas=20, intervalo_seg=3):
    for _ in range(max_tentativas):
        resp = requests.get(
            f"{GRAPH_BASE}/{container_id}",
            params={"fields": "status_code", "access_token": IG_ACCESS_TOKEN},
        )
        dados = resp.json()
        status = dados.get("status_code")
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise RuntimeError(f"Container {container_id} falhou: {dados}")
        time.sleep(intervalo_seg)
    raise TimeoutError(f"Container {container_id} nao ficou pronto a tempo")


def _criar_container_item_carrossel(image_url):
    resp = requests.post(
        f"{GRAPH_BASE}/{IG_USER_ID}/media",
        data={
            "image_url": image_url,
            "is_carousel_item": "true",
            "access_token": IG_ACCESS_TOKEN,
        },
    )
    dados = resp.json()
    if resp.status_code != 200:
        raise RuntimeError(f"Erro ao criar item do carrossel: {dados}")
    return dados["id"]


def publicar_carrossel(urls_imagens, legenda):
    """
    urls_imagens: lista de URLs publicas (2 a 10), na ordem que devem
    aparecer no carrossel -- gere essas URLs com upload_storage.py.
    legenda: texto do post (hashtags inclusas no texto).
    Retorna o ID da publicacao criada.
    """
    _checar_credenciais()
    if not (2 <= len(urls_imagens) <= 10):
        raise ValueError("Carrossel precisa de 2 a 10 imagens")

    ids_itens = []
    for url in urls_imagens:
        item_id = _criar_container_item_carrossel(url)
        _aguardar_container_pronto(item_id)
        ids_itens.append(item_id)

    resp = requests.post(
        f"{GRAPH_BASE}/{IG_USER_ID}/media",
        data={
            "media_type": "CAROUSEL",
            "caption": legenda,
            "children": ",".join(ids_itens),
            "access_token": IG_ACCESS_TOKEN,
        },
    )
    dados = resp.json()
    if resp.status_code != 200:
        raise RuntimeError(f"Erro ao criar container do carrossel: {dados}")
    container_id = dados["id"]
    _aguardar_container_pronto(container_id)

    resp = requests.post(
        f"{GRAPH_BASE}/{IG_USER_ID}/media_publish",
        data={"creation_id": container_id, "access_token": IG_ACCESS_TOKEN},
    )
    dados = resp.json()
    if resp.status_code != 200:
        raise RuntimeError(f"Erro ao publicar carrossel: {dados}")
    return dados["id"]


def publicar_story(url_imagem):
    """
    Publica uma imagem unica como Story (expira em 24h).
    url_imagem: URL publica da imagem, ja gerada em formato retrato
    (9:16 -- 1080x1920) -- a API nao recorta/ajusta proporcao sozinha.
    Sem legenda: a API do Instagram nao renderiza caption em Stories,
    entao qualquer texto precisa ja estar desenhado na propria imagem
    (mesma logica de overlay de texto usada no carrossel).
    Retorna o ID da publicacao criada.
    """
    _checar_credenciais()
    resp = requests.post(
        f"{GRAPH_BASE}/{IG_USER_ID}/media",
        data={
            "image_url": url_imagem,
            "media_type": "STORIES",
            "access_token": IG_ACCESS_TOKEN,
        },
    )
    dados = resp.json()
    if resp.status_code != 200:
        raise RuntimeError(f"Erro ao criar container de story: {dados}")
    container_id = dados["id"]
    _aguardar_container_pronto(container_id)

    resp = requests.post(
        f"{GRAPH_BASE}/{IG_USER_ID}/media_publish",
        data={"creation_id": container_id, "access_token": IG_ACCESS_TOKEN},
    )
    dados = resp.json()
    if resp.status_code != 200:
        raise RuntimeError(f"Erro ao publicar story: {dados}")
    return dados["id"]


def publicar_imagem_unica(url_imagem, legenda):
    """Publica um post de imagem unica (sem carrossel)."""
    _checar_credenciais()
    resp = requests.post(
        f"{GRAPH_BASE}/{IG_USER_ID}/media",
        data={
            "image_url": url_imagem,
            "caption": legenda,
            "access_token": IG_ACCESS_TOKEN,
        },
    )
    dados = resp.json()
    if resp.status_code != 200:
        raise RuntimeError(f"Erro ao criar container de imagem: {dados}")
    container_id = dados["id"]
    _aguardar_container_pronto(container_id)

    resp = requests.post(
        f"{GRAPH_BASE}/{IG_USER_ID}/media_publish",
        data={"creation_id": container_id, "access_token": IG_ACCESS_TOKEN},
    )
    dados = resp.json()
    if resp.status_code != 200:
        raise RuntimeError(f"Erro ao publicar imagem: {dados}")
    return dados["id"]


if __name__ == "__main__":
    print("Testando conexao com a API do Instagram...")
    info = testar_conexao()
    print("Conectado com sucesso:")
    print(f"  username: {info.get('username')}")
    print(f"  account_type: {info.get('account_type')}")
    print(f"  media_count: {info.get('media_count')}")
