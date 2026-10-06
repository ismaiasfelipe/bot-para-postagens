"""
Calendario das 23 campanhas - IL Variedades Enxovais

O QUE ESTE ARQUIVO E
----------------------
Copia local das orientacoes de campanha que vivem no Drive (pasta
"Enxovais Conteudo Bot/campanhas/", documentos "orientacoes-campanha"),
puxadas em 03/09/2026. Guardar aqui evita ter que ler o Drive toda
semana so pra saber se uma campanha esta ativa.

Se o usuario editar as orientacoes no Drive, atualizar aqui manualmente
(nao ha sincronizacao automatica).

TIPOS DE PERIODO
------------------
"dia_fixo"      -- um dia especifico todo ano (mes, dia)
"segundo_domingo" -- segundo domingo de um mes (Dia das Maes)
"ultima_sexta"  -- ultima sexta-feira de um mes (Black Friday)
"intervalo"     -- janela de datas (mes_ini/dia_ini ate mes_fim/dia_fim,
                    pode cruzar o fim do ano, ex: Verao)

12 promocoes relampago mensais ("Dia N do N") + 11 campanhas
sazonais/datas comemorativas = 23 no total.
"""

from datetime import date, timedelta

HASHTAGS_FIXAS = "#ilvariedades #Elegância #Sofisticação #Conforto"

# --- 12 promocoes relampago mensais ("Dia N do N") -------------------------

_PROMOCOES_MENSAIS = [
    {
        "chave": "dia_1_do_1", "nome": "Dia 1 do 1", "mes": 1, "dia": 1,
        "categorias": ["Mesa", "Cama"],
        "produtos_sugeridos": ["Jogo de cozinha", "Jogo de quarto", "Capa de colchão"],
        "cta": "Só hoje! Promoção Dia 1 do 1. Chame no direct e garanta o seu!",
        "hashtags_extras": "#Dia1do1 #PromoçãoRelâmpago",
        "tom_detalhe": "Recomeço de ano, organizar a casa para o ano novo.",
    },
    {
        "chave": "dia_2_do_2", "nome": "Dia 2 do 2", "mes": 2, "dia": 2,
        "categorias": ["Banho", "Mesa"],
        "produtos_sugeridos": ["Toalha de banho", "Toalha de banhão", "Jogo de cozinha"],
        "cta": "Só hoje! Promoção Dia 2 do 2. Chame no direct e garanta o seu!",
        "hashtags_extras": "#Dia2do2 #PromoçãoRelâmpago",
        "tom_detalhe": "Ainda em clima de verão, foco em frescor.",
    },
    {
        "chave": "dia_3_do_3", "nome": "Dia 3 do 3", "mes": 3, "dia": 3,
        "categorias": ["Todas"],
        "produtos_sugeridos": [],
        "cta": "Só hoje! Promoção Dia 3 do 3. Chame no direct e garanta o seu!",
        "hashtags_extras": "#Dia3do3 #PromoçãoRelâmpago",
        "tom_detalhe": "Início do outono, esquenta pro Dia do Consumidor (15/03).",
    },
    {
        "chave": "dia_4_do_4", "nome": "Dia 4 do 4", "mes": 4, "dia": 4,
        "categorias": ["Cama", "Sofá"],
        "produtos_sugeridos": ["Cobertor/manta", "Manta de sofá", "Tapete médio"],
        "cta": "Só hoje! Promoção Dia 4 do 4. Chame no direct e garanta o seu!",
        "hashtags_extras": "#Dia4do4 #PromoçãoRelâmpago",
        "tom_detalhe": "Outono em andamento, foco em aconchego leve.",
    },
    {
        "chave": "dia_5_do_5", "nome": "Dia 5 do 5", "mes": 5, "dia": 5,
        "categorias": ["Cama", "Banho", "Mesa"],
        "produtos_sugeridos": ["Jogo de quarto", "Roupão", "Jogo de cozinha"],
        "cta": "Só hoje! Promoção Dia 5 do 5 -- ótima chance de adiantar o presente das mães. Chame no direct!",
        "hashtags_extras": "#Dia5do5 #PromoçãoRelâmpago",
        "tom_detalhe": "Esquenta para o Dia das Mães (segundo domingo de maio).",
    },
    {
        "chave": "dia_6_do_6", "nome": "Dia 6 do 6", "mes": 6, "dia": 6,
        "categorias": ["Cama", "Sofá"],
        "produtos_sugeridos": ["Jogo de quarto", "Colcha casal pique queen", "Manta de sofá"],
        "cta": "Só hoje! Promoção Dia 6 do 6. Chame no direct e garanta o seu!",
        "hashtags_extras": "#Dia6do6 #PromoçãoRelâmpago",
        "tom_detalhe": "Esquenta para o Dia dos Namorados (12/06) e início do frio.",
    },
    {
        "chave": "dia_7_do_7", "nome": "Dia 7 do 7", "mes": 7, "dia": 7,
        "categorias": ["Cama", "Sofá"],
        "produtos_sugeridos": ["Coberdrom solteiro", "Cobertor/manta", "Colcha preguiada sarja casal/box"],
        "cta": "Só hoje! Promoção Dia 7 do 7. Chame no direct e garanta o seu!",
        "hashtags_extras": "#Dia7do7 #PromoçãoRelâmpago",
        "tom_detalhe": "Férias de julho, inverno pleno, foco máximo em aconchego.",
    },
    {
        "chave": "dia_8_do_8", "nome": "Dia 8 do 8", "mes": 8, "dia": 8,
        "categorias": ["Todas"],
        "produtos_sugeridos": [],
        "cta": "Só hoje! Promoção Dia 8 do 8. Chame no direct e garanta o seu!",
        "hashtags_extras": "#Dia8do8 #PromoçãoRelâmpago",
        "tom_detalhe": "Final do inverno.",
    },
    {
        "chave": "dia_9_do_9", "nome": "Dia 9 do 9", "mes": 9, "dia": 9,
        "categorias": ["Mesa", "Sofá"],
        "produtos_sugeridos": ["Toalha de mesa", "Jogo de cozinha", "Cortina longa"],
        "cta": "Só hoje! Promoção Dia 9 do 9. Chame no direct e garanta o seu!",
        "hashtags_extras": "#Dia9do9 #PromoçãoRelâmpago",
        "tom_detalhe": "Início da primavera, renovação da casa.",
    },
    {
        "chave": "dia_10_do_10", "nome": "Dia 10 do 10", "mes": 10, "dia": 10,
        "categorias": ["Infantil"],
        "produtos_sugeridos": ["Toalha de banho infantil estampada", "Tapete infantil", "Cobertor/manta infantil"],
        "cta": "Só hoje! Promoção Dia 10 do 10 -- adiante o presente da criançada. Chame no direct!",
        "hashtags_extras": "#Dia10do10 #PromoçãoRelâmpago",
        "tom_detalhe": "Esquenta para o Dia das Crianças (12/10).",
    },
    {
        "chave": "dia_11_do_11", "nome": "Dia 11 do 11", "mes": 11, "dia": 11,
        "categorias": ["Todas"],
        "produtos_sugeridos": [],
        "cta": "Só hoje! Promoção Dia 11 do 11 -- esquenta pra Black Friday. Chame no direct!",
        "hashtags_extras": "#Dia11do11 #PromoçãoRelâmpago",
        "tom_detalhe": "Esquenta para a Black Friday (última sexta de novembro).",
    },
    {
        "chave": "dia_12_do_12", "nome": "Dia 12 do 12", "mes": 12, "dia": 12,
        "categorias": ["Mesa", "Cama"],
        "produtos_sugeridos": ["Toalha de mesa 6 cadeiras", "Jogo de cozinha", "Colcha casal pique queen"],
        "cta": "Só hoje! Promoção Dia 12 do 12 -- última chance antes do Natal. Chame no direct!",
        "hashtags_extras": "#Dia12do12 #PromoçãoRelâmpago",
        "tom_detalhe": "Esquenta para o Natal, últimas semanas para presentear.",
    },
]

for _p in _PROMOCOES_MENSAIS:
    _p["periodo"] = {"tipo": "dia_fixo", "mes": _p["mes"], "dia": _p["dia"]}
    _p["formato_sugerido"] = "promocao_relampago"

# --- 11 campanhas sazonais / datas comemorativas ---------------------------

_CAMPANHAS_SAZONAIS = [
    {
        "chave": "dia_das_mulheres", "nome": "Dia das Mulheres",
        "periodo": {"tipo": "dia_fixo", "mes": 3, "dia": 8},
        "categorias": ["Cama", "Banho"],
        "produtos_sugeridos": ["Roupão", "Toalha de banho", "Jogo de quarto", "Colcha casal pique queen"],
        "cta": "Você merece se presentear. Chame no direct e garanta o seu!",
        "hashtags_extras": "#DiaDasMulheres #SePresenteie",
        "tom_detalhe": "Presentear-se, autocuidado, delicadeza.",
        "combina_com": "Roupão, toalha de banho macia, jogo de quarto",
    },
    {
        "chave": "dia_do_consumidor", "nome": "Dia do Consumidor",
        "periodo": {"tipo": "dia_fixo", "mes": 3, "dia": 15},
        "categorias": ["Todas"],
        "produtos_sugeridos": [],
        "cta": "Aproveite antes que acabe! Chame no direct e garanta o seu.",
        "hashtags_extras": "#DiaDoConsumidor #PromoçãoImperdível",
        "tom_detalhe": "Promoção geral da loja, senso de urgência e oportunidade única no ano.",
        "combina_com": "Toda a loja",
    },
    {
        "chave": "outono", "nome": "Outono",
        "periodo": {"tipo": "intervalo", "mes_ini": 3, "dia_ini": 20, "mes_fim": 6, "dia_fim": 20},
        "categorias": ["Cama", "Sofá"],
        "produtos_sugeridos": ["Cobertor/manta", "Manta de sofá", "Tapete médio"],
        "cta": "Prepare sua casa pro outono. Chame no direct e garanta o seu!",
        "hashtags_extras": "#Outono #Aconchego",
        "tom_detalhe": "Transição de temperatura, aconchego leve.",
        "combina_com": "Cobertor/manta, manta de sofá, tapete médio",
    },
    {
        "chave": "dia_dos_namorados", "nome": "Dia dos Namorados",
        "periodo": {"tipo": "dia_fixo", "mes": 6, "dia": 12},
        "categorias": ["Cama", "Banho"],
        "produtos_sugeridos": ["Jogo de quarto", "Colcha casal pique queen", "Roupão (par)"],
        "cta": "Presenteie quem você ama. Chame no direct e garanta o seu!",
        "hashtags_extras": "#DiaDosNamorados #PresenteParaCasal",
        "tom_detalhe": "Presente a dois, romance, casal construindo lar juntos.",
        "combina_com": "Jogo de quarto, colcha casal, roupões em par",
    },
    {
        "chave": "inverno", "nome": "Inverno",
        "periodo": {"tipo": "intervalo", "mes_ini": 6, "dia_ini": 21, "mes_fim": 9, "dia_fim": 22},
        "categorias": ["Cama", "Sofá"],
        "produtos_sugeridos": ["Coberdrom solteiro", "Cobertor/manta", "Colcha preguiada sarja casal/box", "Manta de sofá"],
        "cta": "Fique aquecido com a gente. Chame no direct e garanta o seu!",
        "hashtags_extras": "#Inverno #NoiteDeFrio",
        "tom_detalhe": "Aconchego máximo, proteção contra o frio, convite a ficar em casa.",
        "combina_com": "Coberdrom, cobertor/manta, colcha preguiada",
    },
    {
        "chave": "dia_das_maes", "nome": "Dia das Mães",
        "periodo": {"tipo": "segundo_domingo", "mes": 5},
        "categorias": ["Cama", "Banho", "Mesa"],
        "produtos_sugeridos": ["Jogo de quarto", "Roupão", "Toalha de banho", "Jogo de cozinha"],
        "cta": "Presenteie quem mais te cuida. Chame no direct e garanta o seu!",
        "hashtags_extras": "#DiaDasMães #PresenteParaMãe",
        "tom_detalhe": "Gratidão, homenagem, presente com significado afetivo.",
        "combina_com": "Jogo de quarto, roupão, toalha de banho, jogo de cozinha",
    },
    {
        "chave": "primavera", "nome": "Primavera",
        "periodo": {"tipo": "intervalo", "mes_ini": 9, "dia_ini": 23, "mes_fim": 12, "dia_fim": 20},
        "categorias": ["Mesa", "Sofá"],
        "produtos_sugeridos": ["Toalha de mesa (4 ou 6 cadeiras)", "Jogo de cozinha", "Cortina longa", "Tapete médio"],
        "cta": "Hora de renovar sua casa. Chame no direct e garanta o seu!",
        "hashtags_extras": "#Primavera #CasaNova",
        "tom_detalhe": "Renovação da casa, leveza, entrada de nova estação.",
        "combina_com": "Toalha de mesa, jogo de cozinha, cortina longa, tapete médio",
    },
    {
        "chave": "dia_das_criancas", "nome": "Dia das Crianças",
        "periodo": {"tipo": "dia_fixo", "mes": 10, "dia": 12},
        "categorias": ["Infantil"],
        "produtos_sugeridos": ["Toalha de banho infantil estampada", "Tapete infantil", "Cobertor/manta infantil"],
        "cta": "Presenteie a criançada. Chame no direct e garanta o seu!",
        "hashtags_extras": "#DiaDasCrianças #ParaOsPequenos",
        "tom_detalhe": "Fofura, diversão, presente para os pequenos.",
        "combina_com": "Toalha de banho infantil, tapete infantil, cobertor infantil",
    },
    {
        "chave": "black_friday", "nome": "Black Friday",
        "periodo": {"tipo": "ultima_sexta", "mes": 11},
        "categorias": ["Todas"],
        "produtos_sugeridos": [],
        "cta": "Black Friday chegou! Corre que é só hoje. Chame no direct e garanta o seu!",
        "hashtags_extras": "#BlackFriday #DescontãoILVariedades",
        "tom_detalhe": "Maior desconto do ano, urgência extrema, contagem regressiva.",
        "combina_com": "Toda a loja",
        "formato_sugerido": "promocao_relampago",
    },
    {
        "chave": "verao", "nome": "Verão",
        "periodo": {"tipo": "intervalo", "mes_ini": 12, "dia_ini": 21, "mes_fim": 3, "dia_fim": 19},
        "categorias": ["Banho", "Mesa"],
        "produtos_sugeridos": ["Toalha de banho", "Toalha de banhão", "Jogo de cozinha"],
        "cta": "Refresque sua casa nesse verão. Chame no direct e garanta o seu!",
        "hashtags_extras": "#Verão #Frescor",
        "tom_detalhe": "Frescor, leveza, sensação de praia/verão.",
        "combina_com": "Toalha de banho, toalha de banhão, jogo de cozinha",
    },
    {
        "chave": "natal", "nome": "Natal",
        "periodo": {"tipo": "dia_fixo", "mes": 12, "dia": 25},
        "categorias": ["Mesa", "Cama"],
        "produtos_sugeridos": ["Toalha de mesa 6 cadeiras", "Jogo de cozinha", "Colcha casal pique queen"],
        "cta": "Prepare sua casa pro Natal em família. Chame no direct e garanta o seu!",
        "hashtags_extras": "#Natal #FamíliaReunida",
        "tom_detalhe": "Família reunida, tradição, presente de fim de ano.",
        "combina_com": "Toalha de mesa, jogo de cozinha, colcha casal",
    },
]

for _c in _CAMPANHAS_SAZONAIS:
    _c.setdefault("formato_sugerido", "campanha_sazonal")

CAMPANHAS = _PROMOCOES_MENSAIS + _CAMPANHAS_SAZONAIS


# --- padroes de negocio (app) -> formatos tecnicos de carrossel --------
#
# "apresentacao_produto" e "promocao" ja estao no rodizio automatico (1
# unica foto hero). "cross_sell" e "estilo_vida" pedem varias fotos/
# produtos por slide -- o pipeline tenta montar automaticamente
# reaproveitando candidatos/fotos_variadas (ver
# executar_pipeline_semanal.escolher_formato e _montar_dados_*), mas com
# qualidade mais variavel que os formatos de 1 foto -- o app avisa disso
# ao usuario antes de marcar essas 2 opcoes.
MAPEAMENTO_PADRAO_FORMATOS = {
    "apresentacao_produto": ["vitrine", "novidade_semana", "detalhe_textura"],
    "promocao": ["promocao_relampago", "campanha_sazonal"],
    "cross_sell": ["kit_combo", "giro_categoria"],
    "estilo_vida": ["inspiracao_decoracao", "ambientes_estilos", "paleta_em_foco"],
}


# --- calculo de datas --------------------------------------------------

def _segundo_domingo(ano: int, mes: int) -> date:
    d = date(ano, mes, 1)
    primeiro_domingo = d + timedelta(days=(6 - d.weekday() + 1) % 7)
    return primeiro_domingo + timedelta(days=7)


def _ultima_sexta(ano: int, mes: int) -> date:
    if mes == 12:
        proximo_mes = date(ano + 1, 1, 1)
    else:
        proximo_mes = date(ano, mes + 1, 1)
    d = proximo_mes - timedelta(days=1)
    while d.weekday() != 4:  # 4 = sexta-feira
        d -= timedelta(days=1)
    return d


def _data_exata_da_campanha(campanha: dict, ano: int) -> date | None:
    """Devolve a data 'ancora' da campanha nesse ano (None para intervalos)."""
    periodo = campanha["periodo"]
    tipo = periodo["tipo"]
    if tipo == "dia_fixo":
        return date(ano, periodo["mes"], periodo["dia"])
    if tipo == "segundo_domingo":
        return _segundo_domingo(ano, periodo["mes"])
    if tipo == "ultima_sexta":
        return _ultima_sexta(ano, periodo["mes"])
    return None  # "intervalo" nao tem uma data unica


def _intervalo_contem(periodo: dict, hoje: date) -> bool:
    ano = hoje.year
    inicio = date(ano, periodo["mes_ini"], periodo["dia_ini"])
    fim = date(ano, periodo["mes_fim"], periodo["dia_fim"])
    if inicio <= fim:
        return inicio <= hoje <= fim
    # intervalo cruza o fim do ano (ex: Verao, 21/12 a 19/03)
    return hoje >= inicio or hoje <= fim


def campanhas_ativas_na_semana(data_referencia: date | None = None) -> list[dict]:
    """
    Devolve as campanhas relevantes pra semana de data_referencia (hoje,
    por padrao). Prioridade:
    1. Campanhas de "dia_fixo"/"segundo_domingo"/"ultima_sexta" cuja data
       cai dentro dos 7 dias a partir de data_referencia (a promocao
       relampago do mes, ou uma data comemorativa) -- essas sao as mais
       especificas/urgentes.
    2. Se nenhuma acima, campanhas de "intervalo" (sazonais) que estao
       ativas nesse dia.
    Pode devolver mais de uma (ex: promocao mensal + campanha sazonal
    coincidindo) -- nesse caso as orientacoes ja foram escritas pra se
    cruzarem (ver PROJETO.md), entao o chamador pode escolher priorizar a
    de dia_fixo.
    """
    hoje = data_referencia or date.today()
    fim_semana = hoje + timedelta(days=7)

    especificas = []
    for campanha in CAMPANHAS:
        data_ancora = _data_exata_da_campanha(campanha, hoje.year)
        if data_ancora is None:
            continue
        if hoje <= data_ancora <= fim_semana:
            especificas.append(campanha)

    if especificas:
        return especificas

    sazonais = [
        c for c in CAMPANHAS
        if c["periodo"]["tipo"] == "intervalo" and _intervalo_contem(c["periodo"], hoje)
    ]
    return sazonais


def _resumo_qualidade(descricao_tecnica: str, limite: int = 140) -> str:
    """
    Extrai uma frase curta pra usar na legenda a partir da ficha tecnica
    REAL do produto (puxada do Drive), em vez da frase generica de
    qualidade de sempre.

    A ficha tecnica vem como um dump tab-separated de cabecalhos+valores
    na mesma ordem (PRODUTO, DESCRIÇÃO, MODELO, CARACTERÍSTICAS, ... --
    mesmo formato que extrair_itens_inclusos, em gerar_carrossel_completo.py,
    ja parseia pro campo CARACTERÍSTICAS). Quando bate esse formato, usa o
    campo DESCRIÇÃO direto; senao (texto solto, formato diferente) cai
    pra pegar a 1a frase que mencione material/acabamento, ou so a 1a frase.

    Sem ficha tecnica (ou sem nada aproveitavel), devolve "" e o
    chamador cai pro texto generico.
    """
    if not descricao_tecnica:
        return ""
    texto = descricao_tecnica.lstrip("﻿").strip()
    if not texto:
        return ""

    celulas = [c.strip() for c in texto.split("\t")]
    cabecalhos_esperados = ["PRODUTO", "DESCRIÇÃO", "MODELO", "CARACTERÍSTICAS"]
    n_cabecalhos = 8  # ver extrair_itens_inclusos, mesma ficha padrao
    if len(celulas) > n_cabecalhos + 1 and celulas[:4] == cabecalhos_esperados:
        valor = " ".join(celulas[n_cabecalhos + 1].split())  # coluna DESCRIÇÃO
        if valor:
            return valor[:limite]

    texto_corrido = " ".join(texto.split())
    palavras_chave = [
        "algodão", "algodao", "microfibra", "percal", "gramatura", "fios",
        "macio", "macia", "aveludado", "antialérgico", "antialergico",
        "renda", "bordado", "100%",
    ]
    frases = [f.strip() for f in texto_corrido.replace(";", ".").split(".") if f.strip()]
    for frase in frases:
        if any(chave in frase.lower() for chave in palavras_chave):
            return frase[:limite]
    return frases[0][:limite] if frases else ""


def montar_legenda(campanha: dict | None, produto: dict | str) -> str:
    """
    Monta a legenda final combinando o tom/CTA/hashtags da campanha ativa
    (se houver) com as hashtags fixas da marca, e com um trecho real da
    ficha tecnica do produto (se houver) em vez da frase generica de
    qualidade de sempre -- ver _resumo_qualidade.

    produto: aceita o dict completo do produto (pra aproveitar a ficha
    tecnica real) ou so o nome como string (retrocompatibilidade) --
    nesse caso cai direto pro texto generico, sem ficha tecnica.
    """
    if isinstance(produto, dict):
        produto_nome = produto["nome"]
        qualidade = _resumo_qualidade(produto.get("descricao_tecnica", ""))
    else:
        produto_nome = produto
        qualidade = ""

    if campanha:
        abertura = campanha.get("tom_detalhe", "")
        corpo = f"{abertura}\n\nConheça o nosso {produto_nome}." if abertura else f"Conheça o nosso {produto_nome}."
        if qualidade:
            corpo += f" {qualidade.rstrip('.')}."
        return (
            f"{corpo}\n\n{campanha['cta']}\n\n"
            f"{campanha['hashtags_extras']} {HASHTAGS_FIXAS}"
        )

    frase_qualidade = qualidade or "com o cuidado e a qualidade de sempre"
    return (
        f"Conheça o nosso {produto_nome}, {frase_qualidade} 🤍\n\n"
        f"Chame no direct e garanta o seu!\n\n{HASHTAGS_FIXAS}"
    )


if __name__ == "__main__":
    ativas = campanhas_ativas_na_semana()
    if ativas:
        print("Campanha(s) ativa(s) nesta semana:")
        for c in ativas:
            print(f"  - {c['nome']} ({c['chave']})")
    else:
        print("Nenhuma campanha ativa nesta semana -- fluxo generico.")
