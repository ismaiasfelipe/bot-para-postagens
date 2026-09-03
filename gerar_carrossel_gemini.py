"""
Gerador de carrossel para Instagram com Gemini - IL Variedades Enxovais

O QUE ESTE SCRIPT FAZ
----------------------
1. Le o banco de produtos reais (produtos_reais.json, gerado por conectar_drive.py)
2. Para cada produto:
   - Se tiver "imagem_ambiente" (a foto real do produto no ambiente, com ou
     sem o diagrama de medidas/estampas sobreposto) E "imagem_estampa" (foto
     crua do tecido): usa EDICAO de imagem -- manda as duas fotos reais pro
     Gemini e pede pra recriar a cena limpa, fiel ao tecido real (evita a IA
     "inventar" um padrao novo baseado so em texto/cores da marca).
   - Se so tiver uma das duas, ou nenhuma: cai pra geracao por texto (menos
     fiel, usado como fallback).
3. Salva os arquivos gerados na pasta ./saida/

COMO RODAR
----------
1. pip install google-genai --break-system-packages
2. Rode conectar_drive.py primeiro para gerar produtos_reais.json
3. Defina sua chave de API:
   export GEMINI_API_KEY="sua_chave_aqui"
   (pegue a chave em https://aistudio.google.com/apikey)
4. python gerar_carrossel_gemini.py

CUSTO
-----
Cada chamada de geracao de imagem tem custo por imagem gerada.
Confira os precos atuais em https://ai.google.dev/pricing antes de rodar em lote.
"""

import json
import mimetypes
import os
import sys
from pathlib import Path

# --- Configuracao ---

PASTA_SAIDA = Path("saida")
PASTA_SAIDA.mkdir(exist_ok=True)

MODELO_IMAGEM = "gemini-2.5-flash-image"  # confira o nome de modelo mais recente na doc oficial
ARQUIVO_BANCO = "produtos_reais.json"

MARCA = {
    "nome": "IL Variedades - Enxovais & Lar",
    "cores": {
        "roxo_nobre": "#582C4D",
        "rosa_quartzo": "#C48B9F",
        "off_white": "#FAF9F6",
    },
    "tom_de_voz": "elegante, caloroso, acolhedor, em primeira pessoa do plural, com emojis discretos (🤍💜✨)",
    "call_to_action_padrao": "Chame no direct e garanta o seu!",
    "hashtags_fixas": ["#ilvariedades", "#Elegância", "#Sofisticação", "#Conforto"],
}


def carregar_banco(caminho: str = ARQUIVO_BANCO) -> dict:
    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)


def limpar_descricao_tecnica(descricao_bruta: str) -> str:
    """
    A descricao vem do export de um Google Doc (tabela) para texto puro,
    entao chega com BOM e tabs/quebras de linha soltas. Aqui so colapsamos
    isso numa frase corrida pra caber no prompt de imagem.
    """
    texto = descricao_bruta.lstrip("﻿").strip()
    return " ".join(texto.split())


def montar_prompt_texto(produto: dict, marca: dict) -> str:
    """Prompt para o fallback de geracao pura por texto (sem fotos de referencia reais)."""
    cores = marca["cores"]

    descricao = limpar_descricao_tecnica(produto.get("descricao_tecnica", ""))
    contexto_produto = f"Detalhes do produto (ficha tecnica): {descricao[:400]}. " if descricao else ""

    cor = produto.get("cor_predominante", "").strip()
    cor_texto = f", cor {cor}" if cor else ""

    return (
        f"Fotografia de produto profissional para e-commerce de enxovais. "
        f"Produto: {produto['nome']} ({produto['categoria']}){cor_texto}. "
        f"{contexto_produto}"
        f"Ambientado em um quarto/casa aconchegante, luz natural suave, composicao minimalista. "
        f"Paleta de cores da cena deve harmonizar com roxo nobre ({cores['roxo_nobre']}) "
        f"e rosa quartzo ({cores['rosa_quartzo']}) como tons de apoio (moveis, texteis, paredes), "
        f"fundo em tom off-white ({cores['off_white']}). "
        f"Estilo elegante, sofisticado, acolhedor -- sem texto, sem logotipo, sem pessoas. "
        f"Proporcao quadrada, adequada para post de Instagram."
    )


def montar_prompt_edicao(produto: dict, trocar_estampa: bool = False) -> str:
    """
    Prompt para o modo de edicao (produto tem foto real do ambiente e/ou da
    estampa). Instrui o Gemini a recriar a cena fielmente, sem inventar
    padrao novo e sem manter marcacoes de diagrama (setas, textos, medidas)
    que possam estar sobrepostas na foto de ambiente.

    trocar_estampa=True: usado quando a foto de "estampa" passada e de uma
    variante DIFERENTE da que aparece na foto de ambiente (troca de cor/
    padrao mantendo a mesma cena) -- reforca que a substituicao deve ser
    total em todas as superficies de tecido, nao so nos detalhes/acabamento.
    """
    descricao = limpar_descricao_tecnica(produto.get("descricao_tecnica", ""))
    contexto_produto = f" Ficha tecnica do produto: {descricao[:400]}." if descricao else ""

    instrucao_estampa = (
        "A foto crua do tecido/estampa e de uma variante DIFERENTE da que "
        "aparece na foto do ambiente -- e uma troca de estampa proposital. "
        "Substitua COMPLETAMENTE o padrao em TODAS as superficies de tecido "
        "do produto (colcha/cobertura, fronhas, cortina, barras e "
        "acabamentos) pelo padrao da foto de referencia da estampa. Nao "
        "deixe nenhuma parte do produto com o padrao antigo da foto de "
        "ambiente -- so o comodo, moveis e enquadramento devem permanecer "
        "os mesmos."
        if trocar_estampa else
        "Se houver tambem uma foto crua do tecido/estampa: use-a como "
        "referencia fiel de padrao, cor e escala real do tecido."
    )

    return (
        f"Voce recebeu foto(s) real(is) de referencia do produto "
        f"'{produto['nome']}' ({produto['categoria']}) de uma loja de "
        f"enxovais.{contexto_produto}\n\n"
        "Se houver uma foto do produto montado num ambiente (cama/quarto/casa): "
        "ela pode ter anotacoes de diagrama sobrepostas (setas, caixas de "
        "texto como 'Estampa 1'/'Estampa 2', linhas e numeros de medida em "
        "cm) e/ou closes de amostra de tecido no topo da imagem. "
        f"{instrucao_estampa} "
        "\n\n"
        "Gere uma nova fotografia de produto, profissional, para e-commerce, "
        "recriando a MESMA cena do produto no ambiente (mesmo comodo, mesmos "
        "moveis, mesmo angulo de camera, mesmo enquadramento e proporcoes "
        "quando essa foto existir), porem: "
        "(a) remova completamente qualquer seta, caixa de texto, legenda ou "
        "linha/numero de medida -- a imagem final deve ser UMA UNICA "
        "fotografia limpa, de corpo inteiro da cena, SEM nenhum elemento de "
        "diagrama e SEM nenhum close/inset de amostra de tecido separado "
        "(nao monte um colgate ou grade com varias fotos -- so a foto do "
        "produto no ambiente); "
        "(b) garanta que o tecido siga fielmente o padrao, cores e escala "
        "reais mostrados nas fotos de referencia, sem inventar um padrao novo. "
        "ISSO E CRITICO: e um tecido estampado industrial, com um motivo que "
        "se REPETE em tamanho e espacamento CONSTANTES por toda a superficie "
        "(como um papel de parede) -- nao reinterprete, redesenhe ou varie o "
        "tamanho das flores/motivos entre a colcha e a fronha, e preserve os "
        "tracos finos (contorno, folhas, linhas) exatamente como aparecem na "
        "foto de referencia da estampa, na mesma escala relativa ao tecido; "
        "(c) iluminacao natural suave, estilo elegante e sofisticado, sem "
        "pessoas, sem logotipo, sem texto. "
        "Proporcao quadrada, adequada para post de Instagram."
    )


def montar_prompt_troca_estampa(produto: dict, correcao: str | None = None) -> str:
    """
    Prompt pra trocar a variante de cor/estampa COMPLETA de um produto
    (corpo do tecido + barra/acabamento), reaproveitando uma foto de
    ambiente ja existente. Ver PROJETO.md ("Tecnica de troca de estampa
    completa validada") pro raciocinio e exemplos por tras dessa tecnica.

    Se o resultado sair distorcido (motivo com tamanho inconsistente,
    elemento que nao trocou, etc.), ajuste o texto abaixo e rode de novo
    -- essa funcao e so o ponto de partida, nao uma solucao definitiva.

    correcao=None: modo 1a passada -- troca tudo a partir da foto de
    ambiente original (produto['imagem_ambiente']).
    correcao="texto livre": modo 2a passada -- a IMAGEM 1 usada como base
    ja esta parcialmente correta (normalmente o resultado bom da 1a
    passada); o texto de 'correcao' descreve o que ainda falta ajustar,
    ex: "a cortina ainda esta com o padrao antigo, corrija so ela".
    """
    descricao = limpar_descricao_tecnica(produto.get("descricao_tecnica", ""))
    contexto_produto = f" Ficha tecnica do produto: {descricao[:400]}." if descricao else ""

    if correcao:
        instrucao_cena = (
            f"IMAGEM 1: uma fotografia do produto que JA ESTA CORRETA na "
            f"maior parte -- mantenha tudo IDENTICO (pixel a pixel), "
            f"EXCETO o seguinte, que precisa ser corrigido: {correcao}"
        )
    else:
        instrucao_cena = (
            "IMAGEM 1: foto real do produto (numa variante de cor "
            "DIFERENTE da desejada) montado no ambiente. Pode ter closes "
            "de amostra de tecido e/ou anotacoes de diagrama sobrepostas "
            "(setas, texto, medidas em cm) -- ignore e remova tudo isso."
        )

    return (
        f"Voce recebeu 3 imagens de referencia de um produto de enxoval "
        f"('{produto['nome']}', {produto['categoria']}) de uma loja de "
        f"enxovais.{contexto_produto}\n"
        f"{instrucao_cena}\n"
        "IMAGEM 2: foto real, plana, do CORPO/PADRAO do tecido da NOVA "
        "variante (a estampa principal que cobre a maior parte do produto).\n"
        "IMAGEM 3: foto real da BARRA/ACABAMENTO liso (com ou sem renda) "
        "da NOVA variante (a cor solida de detalhe/borda/acabamento).\n\n"
        "Gere uma nova fotografia de produto, profissional, para "
        "e-commerce, recriando a MESMA cena (mesmo comodo, moveis, angulo "
        "de camera, enquadramento), com o produto na NOVA variante: "
        "(a) as superficies principais de tecido devem seguir fielmente o "
        "padrao da IMAGEM 2 -- e um tecido estampado industrial com "
        "motivo que se REPETE em tamanho e espacamento CONSTANTES por "
        "toda a superficie (como um papel de parede), sem reinterpretar "
        "ou variar o tamanho dos motivos entre as diferentes pecas do "
        "produto, preservando os tracos finos (contorno, folhas, linhas) "
        "na mesma escala da referencia; "
        "(b) as barras/acabamentos/detalhes devem usar a cor solida (e "
        "renda, se houver) da IMAGEM 3, substituindo COMPLETAMENTE a cor "
        "antiga -- nenhuma parte pode ficar com a cor antiga; "
        "(c) remova completamente qualquer seta, caixa de texto, legenda, "
        "linha/numero de medida ou close de amostra -- a imagem final "
        "deve ser UMA UNICA fotografia limpa, sem colagem/grade de varias "
        "fotos; "
        "(d) iluminacao natural suave, estilo elegante e sofisticado, sem "
        "pessoas, sem logotipo, sem texto, proporcao quadrada."
    )


def trocar_estampa_produto(
    produto: dict,
    estampa_corpo: str,
    estampa_barra: str,
    nome_arquivo: str,
    imagem_base: str | None = None,
    correcao: str | None = None,
) -> None:
    """
    Troca a estampa/variante completa de um produto que ja tem foto de
    ambiente, usando o fluxo de 2 passadas validado (ver PROJETO.md):

    1a passada (gera a variante nova a partir do ambiente original):
        trocar_estampa_produto(produto, estampa_corpo, estampa_barra, "p006_v1")

    2a passada (se algum elemento ficou com o padrao antigo, corrige sem
    perder o que ja saiu certo -- reusa o resultado bom como nova base):
        trocar_estampa_produto(
            produto, estampa_corpo, estampa_barra, "p006_v2",
            imagem_base="saida/p006_v1_0.png",
            correcao="a cortina ainda esta com o padrao antigo, corrija so ela",
        )

    Se sair distorcido, mexa em montar_prompt_troca_estampa() e rode de
    novo -- geracao de IA tem variacao aleatoria, e as vezes so rodar de
    novo com o mesmo prompt ja resolve.
    """
    base = imagem_base or produto.get("imagem_ambiente")
    if not base:
        raise ValueError(
            f"Produto {produto['id']} nao tem imagem_ambiente nem imagem_base informada"
        )

    prompt = montar_prompt_troca_estampa(produto, correcao=correcao)
    gerar_imagem_editada(prompt, [base, estampa_corpo, estampa_barra], nome_arquivo=nome_arquivo)


def montar_prompt_verificacao(produto: dict) -> str:
    """Prompt do 'juiz' que confere se a troca de estampa saiu consistente
    em TODA a peca, antes de mostrar o resultado pro usuario."""
    return (
        f"Voce e um revisor de qualidade de fotos de produto para "
        f"e-commerce de enxovais. Vai analisar 3 imagens sobre o produto "
        f"'{produto['nome']}'.\n"
        "IMAGEM 1: a foto FINAL gerada, que deveria mostrar o produto "
        "inteiro (colcha, fronhas, cortina, saia/rodape da cama, quando "
        "aplicavel) numa unica variante de cor/estampa nova e consistente.\n"
        "IMAGEM 2: referencia real do CORPO/PADRAO que deveria aparecer "
        "nas superficies principais (colcha, fronhas, cortina).\n"
        "IMAGEM 3: referencia real da BARRA/ACABAMENTO solido que deveria "
        "aparecer nas bordas/barras/saia da cama.\n\n"
        "Confira PEÇA POR PEÇA visível na IMAGEM 1 (colcha, cada fronha, "
        "cortina -- topo E corpo, saia/rodape da cama) se a cor/padrao "
        "bate com as referencias (IMAGEM 2 pro corpo, IMAGEM 3 pra "
        "barra/acabamento). Um erro comum e alguma peca (normalmente a "
        "cortina ou a saia da cama) ficar com a cor ANTIGA, diferente do "
        "resto -- preste atencao especial nisso.\n\n"
        "Responda EXATAMENTE nesse formato, sem mais nada:\n"
        "LINHA 1: 'SIM' se TODAS as pecas estao consistentes com as "
        "referencias, ou 'NAO' se alguma peca ainda esta com a cor/padrao "
        "errado.\n"
        "LINHA 2: se NAO, uma frase curta e especifica dizendo qual "
        "peca(s) estao erradas e com que cor ficaram (pra poder corrigir). "
        "Se SIM, deixe a linha 2 vazia."
    )


def verificar_troca_estampa(
    imagem_gerada: str, estampa_corpo: str, estampa_barra: str, produto: dict
) -> tuple[bool, str]:
    """
    Pede pro Gemini conferir (so texto, sem gerar imagem -- bem mais
    barato que uma geracao) se a troca de estampa ficou consistente em
    toda a peca. Retorna (passou, motivo_se_falhou).
    """
    client = _obter_cliente()
    partes = []
    for caminho in (imagem_gerada, estampa_corpo, estampa_barra):
        dados, mime_type = _carregar_bytes_imagem(caminho)
        partes.append(_part_de_bytes(dados, mime_type))
    partes.append(montar_prompt_verificacao(produto))

    resposta = client.models.generate_content(model=MODELO_IMAGEM, contents=partes)
    texto = (resposta.text or "").strip()
    linhas = texto.splitlines()
    passou = bool(linhas) and linhas[0].strip().upper().startswith("SIM")
    motivo = linhas[1].strip() if len(linhas) > 1 else ""
    return passou, motivo


def trocar_estampa_com_verificacao(
    produto: dict,
    estampa_corpo: str,
    estampa_barra: str,
    nome_arquivo: str,
    max_tentativas: int = 3,
) -> str:
    """
    Versao com filtro automatico de qualidade de trocar_estampa_produto():
    gera, pede pro Gemini conferir peca por peca contra as referencias, e
    se achar inconsistencia, tenta corrigir automaticamente (reusando o
    resultado anterior como base + o motivo da falha como instrucao de
    correcao) ate max_tentativas vezes. Imprime o progresso e retorna o
    caminho do melhor resultado (ultima tentativa, mesmo se nao passar).
    """
    imagem_base = None
    correcao = None
    caminho_atual = None

    for tentativa in range(1, max_tentativas + 1):
        nome = f"{nome_arquivo}_tentativa{tentativa}"
        print(f"  [tentativa {tentativa}/{max_tentativas}] gerando...")
        prompt = montar_prompt_troca_estampa(produto, correcao=correcao)
        base = imagem_base or produto.get("imagem_ambiente")
        resposta = _gerar_e_retornar_caminho(prompt, [base, estampa_corpo, estampa_barra], nome)
        if resposta is None:
            continue
        caminho_atual = resposta

        passou, motivo = verificar_troca_estampa(caminho_atual, estampa_corpo, estampa_barra, produto)
        if passou:
            print(f"  [tentativa {tentativa}] passou na verificacao.")
            return caminho_atual

        print(f"  [tentativa {tentativa}] reprovado: {motivo}")
        imagem_base = caminho_atual
        correcao = motivo or "algumas pecas ainda estao com a cor/padrao antigo, corrija"

    print(f"  aviso: nao passou na verificacao apos {max_tentativas} tentativas -- "
          f"revise visualmente {caminho_atual} antes de usar")
    return caminho_atual


def _part_de_bytes(dados: bytes, mime_type: str):
    from google.genai import types

    return types.Part.from_bytes(data=dados, mime_type=mime_type)


def _gerar_e_retornar_caminho(prompt: str, caminhos_referencia: list[str], nome_arquivo: str) -> str | None:
    """Como gerar_imagem_editada, mas retorna o caminho do arquivo salvo (ou None)."""
    client = _obter_cliente()
    partes = []
    for caminho in caminhos_referencia:
        dados, mime_type = _carregar_bytes_imagem(caminho)
        partes.append(_part_de_bytes(dados, mime_type))
    partes.append(prompt)

    resposta = client.models.generate_content(model=MODELO_IMAGEM, contents=partes)
    for i, parte in enumerate(resposta.candidates[0].content.parts):
        if parte.inline_data is not None:
            caminho = PASTA_SAIDA / f"{nome_arquivo}_{i}.png"
            with open(caminho, "wb") as f:
                f.write(parte.inline_data.data)
            print(f"  -> salvo em {caminho}")
            return str(caminho)
    print("  -> nenhuma imagem retornada pela API")
    return None


def _carregar_bytes_imagem(caminho: str):
    with open(caminho, "rb") as f:
        dados = f.read()
    mime_type = mimetypes.guess_type(caminho)[0] or "image/jpeg"
    return dados, mime_type


def _obter_cliente():
    try:
        from google import genai
    except ImportError:
        sys.exit(
            "Pacote 'google-genai' nao encontrado. "
            "Instale com: pip install google-genai --break-system-packages"
        )

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        sys.exit(
            "Variavel de ambiente GEMINI_API_KEY nao definida.\n"
            "Rode: export GEMINI_API_KEY='sua_chave_aqui'"
        )

    return genai.Client(api_key=api_key)


def _salvar_resposta(resposta, nome_arquivo: str):
    salvou_alguma = False
    for i, parte in enumerate(resposta.candidates[0].content.parts):
        if parte.inline_data is not None:
            caminho = PASTA_SAIDA / f"{nome_arquivo}_{i}.png"
            with open(caminho, "wb") as f:
                f.write(parte.inline_data.data)
            print(f"  -> salvo em {caminho}")
            salvou_alguma = True
    if not salvou_alguma:
        print("  -> nenhuma imagem retornada pela API")


def gerar_imagem_texto(prompt: str, nome_arquivo: str):
    """Gera a imagem so a partir de texto (sem fotos reais de referencia)."""
    client = _obter_cliente()
    resposta = client.models.generate_content(model=MODELO_IMAGEM, contents=prompt)
    _salvar_resposta(resposta, nome_arquivo)


def gerar_imagem_editada(prompt: str, caminhos_referencia: list[str], nome_arquivo: str):
    """Gera a imagem usando 1+ fotos reais como referencia (edicao/composicao)."""
    from google.genai import types

    client = _obter_cliente()

    partes = []
    for caminho in caminhos_referencia:
        dados, mime_type = _carregar_bytes_imagem(caminho)
        partes.append(types.Part.from_bytes(data=dados, mime_type=mime_type))
    partes.append(prompt)

    resposta = client.models.generate_content(model=MODELO_IMAGEM, contents=partes)
    _salvar_resposta(resposta, nome_arquivo)


def gerar_carrossel():
    dados = carregar_banco()
    produtos = dados["produtos"]

    print(f"Gerando carrossel com {len(produtos)} slides para {MARCA['nome']}\n")

    for produto in produtos:
        print(f"[{produto['id']}] {produto['nome']}")

        referencias = [
            caminho for caminho in (produto.get("imagem_ambiente"), produto.get("imagem_estampa"))
            if caminho
        ]

        if referencias:
            prompt = montar_prompt_edicao(produto)
            print(f"  modo: edicao com {len(referencias)} foto(s) real(is)")
            gerar_imagem_editada(prompt, referencias, nome_arquivo=produto["id"])
        else:
            prompt = montar_prompt_texto(produto, MARCA)
            print("  modo: geracao por texto (sem fotos reais disponiveis)")
            gerar_imagem_texto(prompt, nome_arquivo=produto["id"])

        print()

    print("Concluido. Proximo passo: montar as legendas (tom de voz da marca)")
    print(f"CTA padrao sugerido: \"{MARCA['call_to_action_padrao']}\"")


if __name__ == "__main__":
    gerar_carrossel()
