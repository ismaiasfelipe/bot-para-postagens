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

function configurarFormDefinirPostagens() {
  const selectCampanha = document.getElementById("select-campanha");
  CAMPANHAS.forEach((c) => {
    const opcao = document.createElement("option");
    opcao.value = c.chave;
    opcao.textContent = c.nome;
    selectCampanha.appendChild(opcao);
  });

  const selectCategoria = document.getElementById("select-categoria");
  CATEGORIAS.forEach((cat) => {
    const opcao = document.createElement("option");
    opcao.value = cat;
    opcao.textContent = cat;
    selectCategoria.appendChild(opcao);
  });

  document.getElementById("form-definir-postagens").addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const status = document.getElementById("definir-status");
    const campanha = selectCampanha.value;
    const categoria = selectCategoria.value;
    const produto = document.getElementById("input-produto").value.trim();

    status.textContent = "Enviando pro GitHub Actions...";
    status.className = "status";
    try {
      await dispararWorkflow("definir_tema.yml", { campanha, categoria, produto });
      status.textContent =
        "Tema da semana enviado! O pipeline diário (seg-sáb, 7h) vai usar essa escolha a partir da próxima publicação.";
      status.className = "status sucesso";
    } catch (erro) {
      status.textContent = `Não consegui enviar: ${erro.message}`;
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
  const contagemFormato = {};
  historico.forEach((h) => {
    contagemFormato[h.formato] = (contagemFormato[h.formato] || 0) + 1;
  });

  const resumoHtml = `
    <div class="resumo-cards">
      <div class="card-stat">
        <span class="card-stat-numero">${totalPosts}</span>
        <span class="card-stat-label">carrosséis publicados</span>
      </div>
      <div class="card-stat">
        <span class="card-stat-numero">${totalStories}</span>
        <span class="card-stat-label">stories publicados</span>
      </div>
    </div>
  `;

  const linhasHtml = [...historico]
    .reverse()
    .map((h) => {
      const nomeFormato = NOMES_FORMATO[h.formato] || h.formato || "—";
      const nStories = h.story_ids?.length || 0;
      return `
        <div class="item-historico">
          <div class="item-historico-topo">
            <strong>${escapeHtml(h.produto_id || "—")}</strong>
            <span class="item-historico-data">${escapeHtml(h.data || "—")}</span>
          </div>
          <div class="item-historico-detalhe">
            ${escapeHtml(nomeFormato)}${h.campanha ? ` · ${escapeHtml(h.campanha)}` : ""}
          </div>
          <div class="item-historico-rodape">
            post ${escapeHtml(h.post_id || "—")}${nStories ? ` · ${nStories} stories` : ""}
          </div>
        </div>
      `;
    })
    .join("");

  container.innerHTML = `${resumoHtml}<div class="lista-historico">${linhasHtml}</div>`;
}

function escapeHtml(texto) {
  const div = document.createElement("div");
  div.textContent = String(texto);
  return div.innerHTML;
}
