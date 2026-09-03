"""
Upload de imagens pro Google Cloud Storage - IL Variedades Enxovais

O QUE ESTE SCRIPT FAZ
----------------------
Sobe um arquivo local (uma imagem de carrossel ja gerada) pro bucket
publico do Google Cloud Storage e devolve a URL publica -- e essa URL
que a API do Instagram vai usar pra publicar (ela nao aceita upload
direto de arquivo, so link publico).

CONFIGURACAO
------------
Reaproveita a mesma conta de servico do Drive (credenciais_drive.json),
so pedindo um escopo diferente (Cloud Storage em vez de Drive). O bucket
"il-variedades-carrossel" ja foi criado manualmente no Console com
acesso publico de leitura (allUsers = Storage Object Viewer) e a conta
de servico com permissao de escrita (Storage Object Admin).

COMO RODAR
----------
pip install google-cloud-storage --break-system-packages
python upload_storage.py   # roda o exemplo no fim do arquivo
"""

from pathlib import Path

from google.cloud import storage
from google.oauth2 import service_account

ARQUIVO_CREDENCIAIS = "credenciais_drive.json"
NOME_BUCKET = "il-variedades-carrossel"
SCOPES = ["https://www.googleapis.com/auth/devstorage.read_write"]


def _obter_cliente() -> storage.Client:
    credenciais = service_account.Credentials.from_service_account_file(
        ARQUIVO_CREDENCIAIS, scopes=SCOPES
    )
    return storage.Client(credentials=credenciais, project=credenciais.project_id)


def enviar_para_storage(caminho_local: str, nome_bucket: str = NOME_BUCKET) -> str:
    """
    Sobe o arquivo pro bucket (mesmo nome do arquivo local, dentro de
    uma pasta "carrossel/") e devolve a URL publica.
    """
    cliente = _obter_cliente()
    bucket = cliente.bucket(nome_bucket)

    nome_no_bucket = f"carrossel/{Path(caminho_local).name}"
    blob = bucket.blob(nome_no_bucket)
    blob.upload_from_filename(caminho_local)

    url_publica = f"https://storage.googleapis.com/{nome_bucket}/{nome_no_bucket}"
    print(f"  -> enviado: {url_publica}")
    return url_publica


def enviar_carrossel(caminhos_slides: list[str], nome_bucket: str = NOME_BUCKET) -> list[str]:
    """Sobe uma lista de slides (um carrossel inteiro) e devolve as URLs na mesma ordem."""
    return [enviar_para_storage(caminho, nome_bucket) for caminho in caminhos_slides]


if __name__ == "__main__":
    url = enviar_para_storage("saida/carrossel_p009_vitrine/slide1.png")
    print("\nTeste concluido. URL publica:")
    print(url)
