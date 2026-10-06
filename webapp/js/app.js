// Logica de tela do app -- troca de aba, formularios, leitura do
// historico. Tudo client-side, sem build step (sem bundler/framework)
// de proposito: app pequeno, mantido direto pelo Claude Code, menos
// peca pra quebrar.

const NOMES_FORMATO = {
  vitrine: "Vitrine",
  campanha_sazonal: "Campanha sazonal",
  novidade_semana: "Novidade da semana",
  detalhe_textura: "Detalhe & textura",
  promocao_relampago: "Promoção relâmpago",
  kit_combo: "Kit/combo",
  inspiracao_decoracao: "Inspiração/decoração",
  giro_categoria: "Giro pela categoria",
  paleta_em_foco: "Paleta em foco",
  ambientes_estilos: "Ambientes & estilos",
};

document.addEventListener("DOMContentLoaded", () => {
  configurarNavegacao();
  configurarTelaSetup();
  configurarFormDefinirPostagens();
  configurarChat();

  if (estaConfigurado()) {
    mostrarApp();
  } else {
    mostrarSetup();
  }

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("service-worker.js").catch(() => {});
  }
});

// --- Navegacao entre abas ---------------------------------------------

function configurarNavegacao() {
  document.querySelectorAll(".aba-botao").forEach((botao) => {
    botao.addEventListener("click", () => {
      const aba = botao.dataset.aba;
      document.querySelectorAll(".aba-botao").forEach((b) => b.classList.toggle("ativo", b === botao));
      document.querySelectorAll(".aba-conteudo").forEach((secao) => {
        secao.classList.toggle("ativo", secao.id === `aba-${aba}`);
      });
      if (aba === "relatorio") carregarRelatorio();
    });
  });

  document.getElementById("btn-config")?.addEventListener("click", () => {
    mostrarSetup(true);
  });
}

function mostrarApp() {
  document.getElementById("tela-setup").classList.remove("ativo");
  document.getElementById("app-principal").classList.add("ativo");
  // so agora da pra chamar a API (precisa do token configurado) --
  // ver configurarFormDefinirPostagens, que so monta o HTML estatico.
  _renderizarProdutosPorCategoria();
  _atualizarBadgeStatusSemana();
}

function mostrarSetup(vindoDoApp = false) {
  document.getElementById("app-principal").classList.remove("ativo");
  document.getElementById("tela-setup").classList.add("ativo");
  document.getElementById("btn-voltar-setup").style.display = vindoDoApp ? "inline-block" : "none";
}

// --- Tela de configuracao (token do GitHub) ----------------------------

function configurarTelaSetup() {
  const config = carregarConfig();
  if (config) {
    document.getElementById("input-owner").value = config.owner || "";
    document.getElementById("input-repo").value = config.repo || "";
    document.getElementById("input-branch").value = config.branch || "main";
  }

  document.getElementById("btn-voltar-setup").addEventListener("click", () => mostrarApp());

  document.getElementById("form-setup").addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const status = document.getElementById("setup-status");
    const token = document.getElementById("input-token").value.trim();
    const owner = document.getElementById("input-owner").value.trim();
    const repo = document.getElementById("input-repo").value.trim();
    const branch = document.getElementById("input-branch").value.trim() || "main";

    if (!token || !owner || !repo) {
      status.textContent = "Preencha token, dono e nome do repositório.";
      status.className = "status erro";
      return;
    }

    salvarConfig({ token, owner, repo, branch });
    status.textContent = "Verificando acesso...";
    status.className = "status";

    try {
      await testarAcesso();
      status.textContent = "Conectado! Abrindo o app...";
      status.className = "status sucesso";
      setTimeout(mostrarApp, 600);
    } catch (erro) {
      status.textContent = `Não consegui acessar o repositório: ${erro.message}`;
      status.className = "status erro";
    }
  });
}

// --- Aba "Definir postagens" -------------------------------------------
//
// Formulario com selecao multipla (campanha/padrao/categoria/produto),
// linguagem (tom de voz) e dia de preco -- escreve tema_semana.json
// direto pela API do GitHub (ver github-api.js escreverArquivoRepo),
// sem passar pelo workflow_dispatch antigo (so aceitava 1 valor por
// campo). Formato do JSON tem que bater com tema_semana.py (backend).

function _criarCheckbox(grupo, nome, valor, rotulo, marcadoPorPadrao, aviso) {
  const label = document.createElement("label");
  label.className = "opcao-checkbox";
  const input = document.createElement("input");
  input.type = "checkbox";
  input.name = nome;
  input.value = valor;
  input.checked = !!marcadoPorPadrao;
  label.appendChild(input);
  label.appendChild(document.createTextNode(" " + rotulo));
  if (aviso) {
    const spanAviso = document.createElement("span");
    spanAviso.className = "aviso-inline";
    spanAviso.textContent = " ⚠ pode exigir checagem manual do resultado";
    label.appendChild(spanAviso);
  }
  grupo.appendChild(label);
  return input;
}

function _criarRadio(grupo, nome, valor, rotulo, marcadoPorPadrao) {
  const label = document.createElement("label");
  label.className = "opcao-checkbox";
  const input = document.createElement("input");
  input.type = "radio";
  input.name = nome;
  input.value = valor;
  input.checked = !!marcadoPorPadrao;
  label.appendChild(input);
  label.appendChild(document.createTextNode(" " + rotulo));
  grupo.appendChild(label);
  return input;
}

function _valoresMarcados(nomeGrupo) {
  return Array.from(document.querySelectorAll(`input[name="${nomeGrupo}"]:checked`)).map((i) => i.value);
}

let _produtosCache = null;

/** Mesma logica de _categoria_bate no backend (calendario_campanhas/executar_pipeline_semanal.py). */
function _categoriaBate(categoriaProduto, categoriaSelecionada) {
  return categoriaProduto.toLowerCase().startsWith(categoriaSelecionada.toLowerCase());
}

async function _carregarProdutosCache() {
  if (_produtosCache) return _produtosCache;
  const texto = await lerArquivoRepo("produtos_reais.json");
  _produtosCache = JSON.parse(texto).produtos;
  return _produtosCache;
}

/**
 * Reconstroi o grupo de produtos especificos SEPARADO POR CATEGORIA,
 * mostrando so as categorias marcadas em "grupo-categorias". Cada
 * categoria tem seu proprio "Aleatorio" (marcado por padrao -- nesse
 * caso qualquer produto daquela categoria fica elegivel) ou produtos
 * especificos marcados a mao (desmarca o "Aleatorio" da categoria
 * automaticamente, e vice-versa).
 */
async function _renderizarProdutosPorCategoria() {
  const grupo = document.getElementById("grupo-produtos");
  const categoriasMarcadas = _valoresMarcados("categoria");

  if (categoriasMarcadas.length === 0) {
    grupo.innerHTML = '<p class="aba-intro">Marque uma categoria acima pra ver os produtos dela (ou deixe sem marcar nenhuma pra não restringir por categoria).</p>';
    return;
  }

  let produtos;
  try {
    produtos = await _carregarProdutosCache();
  } catch {
    grupo.innerHTML = '<p class="status erro">Não consegui carregar a lista de produtos.</p>';
    return;
  }

  grupo.innerHTML = "";
  categoriasMarcadas.forEach((categoria) => {
    const produtosDaCategoria = produtos.filter((p) => _categoriaBate(p.categoria, categoria));

    const bloco = document.createElement("div");
    bloco.className = "subgrupo-categoria";
    const titulo = document.createElement("p");
    titulo.className = "subgrupo-titulo";
    titulo.textContent = categoria;
    bloco.appendChild(titulo);

    if (produtosDaCategoria.length === 0) {
      const vazio = document.createElement("p");
      vazio.className = "vazio";
      vazio.textContent = "Nenhum produto cadastrado nessa categoria ainda.";
      bloco.appendChild(vazio);
      grupo.appendChild(bloco);
      return;
    }

    const nomeAleatorio = `aleatorio_cat_${categoria}`;
    const checkAleatorio = _criarCheckbox(bloco, nomeAleatorio, "1", "Aleatório (qualquer produto desta categoria)", true, false);

    const checksProduto = produtosDaCategoria.map((p) =>
      _criarCheckbox(bloco, "produto", p.id, p.nome, false, false)
    );

    checkAleatorio.addEventListener("change", () => {
      if (checkAleatorio.checked) checksProduto.forEach((c) => (c.checked = false));
    });
    checksProduto.forEach((c) =>
      c.addEventListener("change", () => {
        if (c.checked) checkAleatorio.checked = false;
      })
    );

    grupo.appendChild(bloco);
  });
}

function _calcularStatusSemana(definidoEm) {
  const hoje = new Date();
  const diaSemana = hoje.getDay(); // 0=domingo .. 6=sabado
  const diasDesdeSabado = (diaSemana + 1) % 7;
  const anchorSabado = new Date(hoje);
  anchorSabado.setDate(hoje.getDate() - diasDesdeSabado);
  anchorSabado.setHours(0, 0, 0, 0);

  const definido = definidoEm ? new Date(definidoEm + "T00:00:00") : null;
  if (definido && definido >= anchorSabado) {
    return { cor: "ok", texto: "Tema desta semana já definido" };
  }
  if (diaSemana === 6) {
    return { cor: "amarelo", texto: "Hoje é sábado — defina o tema da próxima semana" };
  }
  return { cor: "vermelho", texto: "Atrasado! Defina o tema da semana" };
}

async function _atualizarBadgeStatusSemana() {
  const badge = document.getElementById("status-semana-badge");
  const detalhe = document.getElementById("status-semana-detalhe");
  try {
    const texto = await lerArquivoRepo("tema_semana.json");
    const tema = JSON.parse(texto);
    const statusCalc = _calcularStatusSemana(tema.definido_em);
    badge.className = `badge-status badge-${statusCalc.cor}`;
    detalhe.textContent = statusCalc.texto;
  } catch {
    const statusCalc = _calcularStatusSemana(null);
    badge.className = `badge-status badge-${statusCalc.cor}`;
    detalhe.textContent = statusCalc.texto;
  }
}

/** Verifica divergencias simples antes de salvar (ver especificacao: "continuar assim mesmo"). */
async function _validarSelecao(selecao) {
  const avisos = [];

  if ((selecao.padroes || []).some((p) => PADROES.find((x) => x.chave === p)?.aviso)) {
    avisos.push(
      "Cross-sell e Estilo de vida/Inspiração usam formatos que podem precisar de várias fotos de produtos diferentes -- o bot tenta montar sozinho, mas o resultado pode variar mais. Vale conferir antes de publicar."
    );
  }

  if ((selecao.produtos_ids || []).length > 0) {
    try {
      const texto = await lerArquivoRepo("produtos_reais.json");
      const banco = JSON.parse(texto);
      selecao.produtos_ids.forEach((id) => {
        const produto = banco.produtos.find((p) => p.id === id);
        if (!produto) {
          avisos.push(`Produto ${id} não foi encontrado no catálogo.`);
        } else if (!produto.imagem_ambiente && !produto.imagem_estampa) {
          avisos.push(`"${produto.nome}" ainda não tem nenhuma foto cadastrada -- a publicação pode falhar.`);
        }
      });
    } catch {
      avisos.push("Não consegui checar o catálogo de produtos agora -- a verificação ficou incompleta.");
    }
  }

  if (selecao.preco_dia) {
    avisos.push(
      "A ficha técnica ainda não tem o campo de preço preenchido pra nenhum produto -- até isso ser adicionado, o preço não vai aparecer mesmo com essa opção marcada."
    );
  }

  return avisos;
}

function _lerSelecaoFormulario() {
  const campanhas = _valoresMarcados("campanha");
  const linguagem = document.querySelector('input[name="linguagem"]:checked')?.value || "neutra";
  const padroes = _valoresMarcados("padrao");
  const categorias_foco = _valoresMarcados("categoria");
  const produtos_ids = _valoresMarcados("produto");
  const preco_dia = document.querySelector('input[name="preco"]:checked')?.value || "";
  return {
    campanhas_chaves: campanhas.length ? campanhas : null,
    linguagem,
    padroes: padroes.length ? padroes : null,
    categorias_foco: categorias_foco.length ? categorias_foco : null,
    produtos_ids: produtos_ids.length ? produtos_ids : null,
    preco_dia: preco_dia || null,
  };
}

async function _salvarTemaSemana(selecao) {
  const definido_em = new Date().toISOString().slice(0, 10);
  const tema = { definido_em, ...selecao };
  await escreverArquivoRepo(
    "tema_semana.json",
    JSON.stringify(tema, null, 2) + "\n",
    "Define tema da semana (via painel)"
  );
  return tema;
}

function configurarFormDefinirPostagens() {
  const grupoCampanhas = document.getElementById("grupo-campanhas");
  _criarCheckbox(grupoCampanhas, "campanha", CAMPANHA_PADRAO_MARCA, "Padrão da marca", true, false);
  CAMPANHAS.forEach((c) => _criarCheckbox(grupoCampanhas, "campanha", c.chave, c.nome, false, false));

  const grupoLinguagem = document.getElementById("grupo-linguagem");
  LINGUAGENS.forEach((l) => _criarRadio(grupoLinguagem, "linguagem", l.chave, l.nome, l.chave === "neutra"));

  const grupoPadroes = document.getElementById("grupo-padroes");
  PADROES.forEach((p) => _criarCheckbox(grupoPadroes, "padrao", p.chave, p.nome, false, p.aviso));

  const grupoCategorias = document.getElementById("grupo-categorias");
  CATEGORIAS.forEach((cat) => {
    const check = _criarCheckbox(grupoCategorias, "categoria", cat, cat, false, false);
    check.addEventListener("change", _renderizarProdutosPorCategoria);
  });

  const grupoPreco = document.getElementById("grupo-preco");
  _criarRadio(grupoPreco, "preco", "", "Sem preço", true);
  DIAS_SEMANA.forEach((d) =>
    _criarRadio(grupoPreco, "preco", d.chave, `Carrossel + story com preço (${d.nome})`, false)
  );

  const form = document.getElementById("form-definir-postagens");
  document.getElementById("btn-status-semana").addEventListener("click", () => {
    const aberto = form.style.display !== "none";
    form.style.display = aberto ? "none" : "flex";
  });
  document.getElementById("btn-cancelar-form-postagens").addEventListener("click", () => {
    form.style.display = "none";
  });

  form.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const status = document.getElementById("definir-status");
    const divDivergencias = document.getElementById("avisos-divergencia");
    const selecao = _lerSelecaoFormulario();

    status.textContent = "Verificando os dados...";
    status.className = "status";
    divDivergencias.style.display = "none";

    const avisos = await _validarSelecao(selecao);
    if (avisos.length > 0 && !form.dataset.ignorarAvisos) {
      divDivergencias.innerHTML =
        "<strong>Encontrei umas divergências:</strong><ul>" +
        avisos.map((a) => `<li>${escapeHtml(a)}</li>`).join("") +
        "</ul>";
      divDivergencias.style.display = "block";
      status.textContent = "Confira os avisos acima antes de continuar.";
      status.className = "status";
      const botaoContinuar = document.createElement("button");
      botaoContinuar.type = "button";
      botaoContinuar.className = "botao-perigo";
      botaoContinuar.textContent = "Continuar assim mesmo";
      botaoContinuar.addEventListener("click", async () => {
        form.dataset.ignorarAvisos = "1";
        form.requestSubmit();
      });
      divDivergencias.appendChild(botaoContinuar);
      return;
    }
    delete form.dataset.ignorarAvisos;

    status.textContent = "Salvando tema da semana...";
    try {
      await _salvarTemaSemana(selecao);
      status.textContent =
        "Tema da semana salvo! O pipeline diário (seg-sáb, 7h) vai usar essa escolha a partir da próxima publicação.";
      status.className = "status sucesso";
      form.style.display = "none";
      _atualizarBadgeStatusSemana();
    } catch (erro) {
      status.textContent = `Não consegui salvar: ${erro.message}`;
      status.className = "status erro";
    }
  });

  document.getElementById("btn-publicar-agora").addEventListener("click", async () => {
    const status = document.getElementById("definir-status");
    if (!confirm("Isso dispara o pipeline AGORA e pode publicar de verdade no Instagram. Confirmar?")) return;
    status.textContent = "Disparando publicação agora...";
    status.className = "status";
    try {
      await dispararWorkflow("pipeline_diario.yml", {});
      status.textContent = "Disparado! Acompanhe o progresso na aba Actions do GitHub.";
      status.className = "status sucesso";
    } catch (erro) {
      status.textContent = `Não consegui disparar: ${erro.message}`;
      status.className = "status erro";
    }
  });
}

// --- Aba "Chat" (placeholder, sem IA conectada nesta 1a fase) ----------

function configurarChat() {
  const form = document.getElementById("form-chat");
  const lista = document.getElementById("chat-mensagens");

  form.addEventListener("submit", (evento) => {
    evento.preventDefault();
    const campo = document.getElementById("input-chat");
    const texto = campo.value.trim();
    if (!texto) return;

    adicionarMensagem(lista, texto, "usuario");
    campo.value = "";

    adicionarMensagem(
      lista,
      "Esse chat ainda não está conectado a uma IA (fase 1 do app é só a interface). " +
        "Por enquanto, use a aba \"Definir postagens\" pra controlar o que vai ser publicado.",
      "bot"
    );
  });
}

function adicionarMensagem(lista, texto, tipo) {
  const item = document.createElement("div");
  item.className = `chat-msg chat-msg-${tipo}`;
  item.textContent = texto;
  lista.appendChild(item);
  lista.scrollTop = lista.scrollHeight;
}

// --- Aba "Relatório" -----------------------------------------------------

async function carregarRelatorio() {
  const container = document.getElementById("relatorio-conteudo");
  container.innerHTML = '<p class="carregando">Carregando histórico...</p>';

  let historico;
  try {
    const texto = await lerArquivoRepo("historico_publicacoes.json");
    historico = JSON.parse(texto);
  } catch (erro) {
    if (String(erro.message).includes("404")) {
      container.innerHTML =
        '<p class="vazio">Ainda não há nenhuma publicação registrada em historico_publicacoes.json.</p>';
    } else {
      container.innerHTML = `<p class="status erro">Não consegui ler o histórico: ${erro.message}</p>`;
    }
    return;
  }

  if (!Array.isArray(historico) || historico.length === 0) {
    container.innerHTML = '<p class="vazio">Ainda não há nenhuma publicação registrada.</p>';
    return;
  }

  const totalPosts = historico.length;
  const totalStories = historico.reduce((soma, h) => soma + (h.story_ids?.length || 0), 0);
  const totalAlcance = historico.reduce((soma, h) => soma + (h.metricas?.reach || 0), 0);
  const totalCurtidas = historico.reduce((soma, h) => soma + (h.metricas?.likes || 0), 0);

  const cardsBasicos = `
    <div class="card-stat">
      <span class="card-stat-numero">${totalPosts}</span>
      <span class="card-stat-label">carrosséis publicados</span>
    </div>
    <div class="card-stat">
      <span class="card-stat-numero">${totalStories}</span>
      <span class="card-stat-label">stories publicados</span>
    </div>
  `;
  // metricas so existem depois que .github/workflows/atualizar_metricas.yml
  // rodar pelo menos 1x (ver relatorio_instagram.py) -- sem isso, so mostra
  // os 2 cards basicos acima.
  const cardsMetricas =
    totalAlcance || totalCurtidas
      ? `
    <div class="card-stat">
      <span class="card-stat-numero">${formatarNumero(totalAlcance)}</span>
      <span class="card-stat-label">alcance total</span>
    </div>
    <div class="card-stat">
      <span class="card-stat-numero">${formatarNumero(totalCurtidas)}</span>
      <span class="card-stat-label">curtidas totais</span>
    </div>
  `
      : "";

  const resumoHtml = `<div class="resumo-cards">${cardsBasicos}${cardsMetricas}</div>`;

  const linhasHtml = [...historico]
    .reverse()
    .map((h) => {
      const nomeFormato = NOMES_FORMATO[h.formato] || h.formato || "—";
      const nStories = h.story_ids?.length || 0;
      const m = h.metricas;
      const metricasHtml = m
        ? `<div class="item-historico-metricas">
            ${m.reach != null ? `<span>👁 ${formatarNumero(m.reach)}</span>` : ""}
            ${m.likes != null ? `<span>❤ ${formatarNumero(m.likes)}</span>` : ""}
            ${m.comments != null ? `<span>💬 ${formatarNumero(m.comments)}</span>` : ""}
            ${m.saved != null ? `<span>🔖 ${formatarNumero(m.saved)}</span>` : ""}
          </div>`
        : "";

      return `
        <div class="item-historico">
          <div class="item-historico-topo">
            <strong>${escapeHtml(h.produto_id || "—")}</strong>
            <span class="item-historico-data">${escapeHtml(h.data || "—")}</span>
          </div>
          <div class="item-historico-detalhe">
            ${escapeHtml(nomeFormato)}${h.campanha ? ` · ${escapeHtml(h.campanha)}` : ""}
          </div>
          ${metricasHtml}
          <div class="item-historico-rodape">
            post ${escapeHtml(h.post_id || "—")}${nStories ? ` · ${nStories} stories` : ""}
          </div>
        </div>
      `;
    })
    .join("");

  container.innerHTML = `${resumoHtml}<div class="lista-historico">${linhasHtml}</div>`;
}

function formatarNumero(n) {
  if (n >= 1000) return `${(n / 1000).toFixed(1).replace(".0", "")}k`;
  return String(n);
}

function escapeHtml(texto) {
  const div = document.createElement("div");
  div.textContent = String(texto);
  return div.innerHTML;
}
