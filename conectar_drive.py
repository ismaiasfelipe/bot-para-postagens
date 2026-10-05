"""
Conector Google Drive -> Banco de produtos (IL Variedades)

O QUE ESTE SCRIPT FAZ
----------------------
Le a estrutura REAL de catalogo que ja existe no Google Drive da loja e
monta a lista de produtos automaticamente, no mesmo formato que
gerar_carrossel_gemini.py espera (substituindo o produtos_exemplo.json).

ESTRUTURA REAL JA EXISTENTE NO DRIVE (confirmada em 04/08/2026)
------------------------------------------------------------------
produtos/                                  <- pasta raiz do catalogo
  cama (quarto)/
    lençol casal 4 pçs/
      estampas/            -> fotos cruas do tecido/produto
      produto no ambiente/ -> fotos do produto em cena/decoracao
      fotos variadas/      -> fotos soltas do produto disperso/empilhado/
                               dobrado (baixadas TODAS, nao so a 1a --
                               servem de referencia de composicao real
                               pra gerar_composicao_dispersa_com_verificacao,
                               ver gerar_carrossel_gemini.py)
      descrição/           -> Google Doc com ficha tecnica
    colcha preguiada sarja casal-box/
    ... (outros produtos da categoria)
  banho (banheiro)/
  mesa (cozinha)/
  sofá (cortinas, tapetes e adereços)/
  infantil/

Cada pasta de categoria contem varias pastas de produto, e cada pasta de
produto contem as 4 subpastas acima (nem todas tem conteudo em todas ainda).

CONFIGURACAO NECESSARIA (fazer uma unica vez)
------------------------------------------------
1. Acesse https://console.cloud.google.com/
2. Crie um projeto nesse Google Cloud (ou use um existente)
3. Ative a "Google Drive API" (menu APIs e servicos > Ativar APIs e servicos)
4. Crie uma "Conta de servico" (Credenciais > Criar credenciais > Conta de
   servico). De um nome tipo "bot-il-variedades"
5. Depois de criada, gere uma chave: clique na conta de servico > Chaves >
   Adicionar chave > Criar nova chave > formato JSON. Isso baixa um arquivo
   .json -- SALVE ele nesta mesma pasta do projeto com o nome
   "credenciais_drive.json" (e nunca compartilhe/publique esse arquivo)
6. Abra o arquivo .json baixado e copie o valor do campo "client_email"
   (algo tipo bot-il-variedades@nome-projeto.iam.gserviceaccount.com)
7. No Google Drive de verdade, va na pasta "produtos" (a pasta raiz do
   catalogo), clique em Compartilhar, e adicione esse e-mail como "Leitor"
   -- compartilhar so a pasta raiz ja da acesso a tudo dentro dela
8. Pegue o ID da pasta raiz "produtos": abra ela no navegador e copie o
   trecho da URL depois de "folders/"

COMO RODAR
----------
pip install google-api-python-client google-auth --break-system-packages
python conectar_drive.py
"""

import io
import json
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# --- Configuracao ---
ARQUIVO_CREDENCIAIS = "credenciais_drive.json"
ID_PASTA_PRODUTOS = "14HEzU31Lu4ieHCLGgKrDFkHI3Q3lOcOk"  # pasta raiz do catalogo "produtos"
PASTA_DOWNLOAD_LOCAL = Path("banco_local")
PASTA_DOWNLOAD_LOCAL.mkdir(exist_ok=True)

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def conectar():
    credenciais = service_account.Credentials.from_service_account_file(
        ARQUIVO_CREDENCIAIS, scopes=SCOPES
    )
    return build("drive", "v3", credentials=credenciais)


def listar_subpastas(servico, id_pasta_pai):
    query = (
        f"'{id_pasta_pai}' in parents "
        "and mimeType = 'application/vnd.google-apps.folder' "
        "and trashed = false"
    )
    resultado = servico.files().list(q=query, fields="files(id, name)").execute()
    return [(f["id"], f["name"]) for f in resultado.get("files", [])]


def listar_imagens(servico, id_pasta):
    query = (
        f"'{id_pasta}' in parents "
        "and (mimeType contains 'image/') "
        "and trashed = false"
    )
    resultado = servico.files().list(
        q=query, fields="files(id, name, mimeType)"
    ).execute()
    return resultado.get("files", [])


def ler_descricao(servico, id_pasta_descricao):
    """Le o conteudo do Google Doc de ficha tecnica, se existir."""
    query = (
        f"'{id_pasta_descricao}' in parents "
        "and mimeType = 'application/vnd.google-apps.document' "
        "and trashed = false"
    )
    resultado = servico.files().list(q=query, fields="files(id, name)").execute()
    arquivos = resultado.get("files", [])
    if not arquivos:
        return ""

    id_doc = arquivos[0]["id"]
    conteudo = servico.files().export(
        fileId=id_doc, mimeType="text/plain"
    ).execute()
    return conteudo.decode("utf-8") if isinstance(conteudo, bytes) else conteudo


def baixar_arquivo(servico, id_arquivo, caminho_destino):
    request = servico.files().get_media(fileId=id_arquivo)
    with io.FileIO(caminho_destino, "wb") as arquivo_local:
        downloader = MediaIoBaseDownload(arquivo_local, request)
        concluido = False
        while not concluido:
            _, concluido = downloader.next_chunk()


def montar_banco_de_produtos() -> dict:
    servico = conectar()
    produtos = []
    contador = 1

    categorias = listar_subpastas(servico, ID_PASTA_PRODUTOS)
    print(f"Encontradas {len(categorias)} categorias no Drive.\n")

    for id_categoria, nome_categoria in categorias:
        produtos_da_categoria = listar_subpastas(servico, id_categoria)
        print(f"[{nome_categoria}] {len(produtos_da_categoria)} produtos")

        for id_produto, nome_produto in produtos_da_categoria:
            subpastas = {nome: id_ for id_, nome in listar_subpastas(servico, id_produto)}
            # subpastas = {"estampas": id, "produto no ambiente": id, ...}

            # imagem_ambiente: a foto/ficha (com o produto montado no ambiente,
            # eventualmente com o diagrama de medidas/estampas sobreposto).
            # imagem_estampa: uma foto crua do tecido, usada como referencia
            # fiel de padrao/cor para a geracao (evita a IA "inventar" estampa).
            caminho_ambiente = _baixar_primeira_imagem(
                servico, subpastas.get("produto no ambiente"),
                PASTA_DOWNLOAD_LOCAL / f"p{contador:03d}_ambiente"
            )
            caminho_estampa = _baixar_primeira_imagem(
                servico, subpastas.get("estampas"),
                PASTA_DOWNLOAD_LOCAL / f"p{contador:03d}_estampa"
            )

            # fotos_variadas: TODAS as fotos da subpasta (nao so 1) -- cada
            # uma costuma mostrar o produto disperso/empilhado/dobrado numa
            # composicao real diferente, usadas como referencia de
            # composicao na geracao (ver montar_prompt_composicao_dispersa).
            fotos_variadas = _baixar_todas_imagens(
                servico, subpastas.get("fotos variadas"),
                PASTA_DOWNLOAD_LOCAL / f"p{contador:03d}_variada"
            )

            if not caminho_ambiente and not caminho_estampa:
                # sem estampas/ambiente: usa a 1a de "fotos variadas" como
                # ultimo recurso pra imagem_estampa tambem
                caminho_estampa = fotos_variadas[0] if fotos_variadas else None

            if not caminho_ambiente and not caminho_estampa:
                print(f"  [!] {nome_produto}: sem foto ainda, pulando")
                continue

            descricao_texto = ""
            id_pasta_descricao = subpastas.get("descrição")
            if id_pasta_descricao:
                descricao_texto = ler_descricao(servico, id_pasta_descricao)

            produtos.append({
                "id": f"p{contador:03d}",
                "categoria": nome_categoria,
                "nome": nome_produto,
                "tags": [nome_categoria.lower()],
                "cor_predominante": "",  # preencher manualmente se quiser mais precisao
                "descricao_tecnica": descricao_texto.strip(),
                "imagem_ambiente": caminho_ambiente,
                "imagem_estampa": caminho_estampa,
                "fotos_variadas": fotos_variadas,
            })
            print(f"  [ok] {nome_produto}"
                  f" (ambiente={'sim' if caminho_ambiente else 'nao'},"
                  f" estampa={'sim' if caminho_estampa else 'nao'},"
                  f" variadas={len(fotos_variadas)})")
            contador += 1

    return {"produtos": produtos}


def _baixar_primeira_imagem(servico, id_subpasta, caminho_base: Path) -> str | None:
    """Baixa a primeira imagem da subpasta (se existir) e retorna o caminho local."""
    if not id_subpasta:
        return None
    imagens = listar_imagens(servico, id_subpasta)
    if not imagens:
        return None
    imagem = imagens[0]
    extensao = Path(imagem["name"]).suffix or ".jpg"
    caminho_local = caminho_base.with_suffix(extensao)
    baixar_arquivo(servico, imagem["id"], str(caminho_local))
    return str(caminho_local)


def _baixar_todas_imagens(servico, id_subpasta, caminho_base: Path) -> list[str]:
    """
    Baixa TODAS as imagens da subpasta (nao so a primeira) -- usado pra
    "fotos variadas", onde cada foto costuma mostrar o produto disperso/
    empilhado/dobrado numa composicao diferente, e essas composicoes reais
    servem de referencia pro Gemini (ver montar_prompt_composicao_dispersa
    em gerar_carrossel_gemini.py) em vez de inventar o arranjo do zero.
    """
    if not id_subpasta:
        return []
    caminhos = []
    for indice, imagem in enumerate(listar_imagens(servico, id_subpasta)):
        extensao = Path(imagem["name"]).suffix or ".jpg"
        caminho_local = caminho_base.with_name(f"{caminho_base.name}_{indice}").with_suffix(extensao)
        baixar_arquivo(servico, imagem["id"], str(caminho_local))
        caminhos.append(str(caminho_local))
    return caminhos


if __name__ == "__main__":
    banco = montar_banco_de_produtos()

    with open("produtos_reais.json", "w", encoding="utf-8") as f:
        json.dump(banco, f, ensure_ascii=False, indent=2)

    print(f"\nConcluido! {len(banco['produtos'])} produtos salvos em produtos_reais.json")
    print("Proximo passo: usar esse arquivo no lugar de produtos_exemplo.json")

