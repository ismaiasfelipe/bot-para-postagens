"""
Ponto de entrada por linha de comando pro workflow "Definir tema da
semana" do GitHub Actions -- ver .github/workflows/definir_tema.yml.
Nao roda nada sozinho fora do CI; e so um wrapper fino sobre tema_semana.py.
"""

import argparse
from datetime import date

from tema_semana import salvar_tema

parser = argparse.ArgumentParser()
parser.add_argument("--campanha", default="")
parser.add_argument("--categoria", default="")
parser.add_argument("--produto", default="")
args = parser.parse_args()

salvar_tema(
    campanha_chave=args.campanha.strip() or None,
    categoria_foco=args.categoria.strip() or None,
    produto_id=args.produto.strip() or None,
    definido_em=date.today().isoformat(),
)

print(
    "Tema da semana salvo:",
    f"campanha={args.campanha or '(nenhuma)'}",
    f"categoria={args.categoria or '(nenhuma)'}",
    f"produto={args.produto or '(nenhum)'}",
)
