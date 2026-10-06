// Gerado a partir de calendario_campanhas.py (CAMPANHAS) -- se adicionar
// ou renomear uma campanha la, atualize aqui tambem (mesmas chaves que o
// workflow definir_tema.yml espera).
const CAMPANHAS = [
  { chave: "dia_1_do_1", nome: "Dia 1 do 1" },
  { chave: "dia_2_do_2", nome: "Dia 2 do 2" },
  { chave: "dia_3_do_3", nome: "Dia 3 do 3" },
  { chave: "dia_4_do_4", nome: "Dia 4 do 4" },
  { chave: "dia_5_do_5", nome: "Dia 5 do 5" },
  { chave: "dia_6_do_6", nome: "Dia 6 do 6" },
  { chave: "dia_7_do_7", nome: "Dia 7 do 7" },
  { chave: "dia_8_do_8", nome: "Dia 8 do 8" },
  { chave: "dia_9_do_9", nome: "Dia 9 do 9" },
  { chave: "dia_10_do_10", nome: "Dia 10 do 10" },
  { chave: "dia_11_do_11", nome: "Dia 11 do 11" },
  { chave: "dia_12_do_12", nome: "Dia 12 do 12" },
  { chave: "dia_das_mulheres", nome: "Dia das Mulheres" },
  { chave: "dia_do_consumidor", nome: "Dia do Consumidor" },
  { chave: "outono", nome: "Outono" },
  { chave: "dia_dos_namorados", nome: "Dia dos Namorados" },
  { chave: "inverno", nome: "Inverno" },
  { chave: "dia_das_maes", nome: "Dia das Mães" },
  { chave: "primavera", nome: "Primavera" },
  { chave: "dia_das_criancas", nome: "Dia das Crianças" },
  { chave: "black_friday", nome: "Black Friday" },
  { chave: "verao", nome: "Verão" },
  { chave: "natal", nome: "Natal" },
];

const CATEGORIAS = ["Cama", "Banho", "Mesa", "Sofá", "Infantil"];

const CAMPANHA_PADRAO_MARCA = "__padrao_marca__";

const LINGUAGENS = [
  { chave: "neutra", nome: "Neutra" },
  { chave: "acolhedora", nome: "Acolhedora" },
  { chave: "chamativa", nome: "Chamativa" },
  { chave: "agressiva", nome: "Agressiva" },
];

// aviso: true nos padroes que ainda exigem montagem automatica mais
// arriscada (varias fotos/produtos por slide) -- ver
// calendario_campanhas.MAPEAMENTO_PADRAO_FORMATOS no backend.
const PADROES = [
  { chave: "apresentacao_produto", nome: "Apresentação de produto", aviso: false },
  { chave: "promocao", nome: "Promoção", aviso: false },
  { chave: "cross_sell", nome: "Cross-sell", aviso: true },
  { chave: "estilo_vida", nome: "Estilo de vida / Inspiração", aviso: true },
];

const DIAS_SEMANA = [
  { chave: "segunda", nome: "Segunda-feira" },
  { chave: "terca", nome: "Terça-feira" },
  { chave: "quarta", nome: "Quarta-feira" },
  { chave: "quinta", nome: "Quinta-feira" },
  { chave: "sexta", nome: "Sexta-feira" },
  { chave: "sabado", nome: "Sábado" },
  { chave: "todos", nome: "Todos os dias" },
];
