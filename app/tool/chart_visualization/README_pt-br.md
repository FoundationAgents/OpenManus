# Ferramenta de Visualização de Gráficos

A ferramenta de visualização de gráficos gera código de processamento de dados através de Python e, por fim, invoca [@visactor/vmind](https://github.com/VisActor/VMind) para obter especificações de gráficos. A renderização dos gráficos é implementada usando [@visactor/vchart](https://github.com/VisActor/VChart).

## Instalação

1. Instale o Node.js >= 18

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
# Após a instalação, reinicie o terminal e instale a versão LTS mais recente do Node.js:
nvm install --lts
```

2. Instale as dependências

```bash
cd app/tool/chart_visualization
npm install
```

## Ferramentas
### python_execute

Execute as partes necessárias da análise de dados (excluindo a visualização de dados) usando código Python, incluindo processamento de dados, resumo de dados, geração de relatórios e algum código de script Python geral.

#### Entrada
```typescript
{
  // Tipo de código: processamento de dados/relatório de dados/outras tarefas gerais
  code_type: "process" | "report" | "others"
  // Código final de execução
  code: string;
}
```

#### Saída
Resultados da execução Python, incluindo o salvamento de arquivos intermediários e resultados de saída impressos.

### visualization_preparation

Uma pré-ferramenta para visualização de dados com dois propósitos:

#### Dados -> Gráfico
Usado para extrair os dados necessários para análise (.csv) e a descrição da visualização correspondente dos dados, gerando finalmente um arquivo de configuração JSON.

#### Gráfico + Insight -> Gráfico
Selecione gráficos existentes e insights de dados correspondentes, escolha insights de dados para adicionar ao gráfico na forma de anotações de dados e, finalmente, gere um arquivo de configuração JSON.

#### Entrada
```typescript
{
  // Tipo de código: visualização de dados ou adição de insight de dados
  code_type: "visualization" | "insight"
  // Código Python usado para produzir o arquivo JSON final
  code: string;
}
```

#### Saída
Um arquivo de configuração para visualização de dados, usado para a ferramenta `data_visualization`.

## data_visualization

Gere visualizações de dados específicas com base no conteúdo de `visualization_preparation`.

### Entrada
```typescript
{
  // Caminho do arquivo de configuração
  json_path: string;
  // Propósito atual, visualização de dados ou adição de anotação de insight
  tool_type: "visualization" | "insight";
  // Produto final png ou html; html suporta renderização e interação vchart
  output_type: 'png' | 'html'
  // Idioma, atualmente suporta chinês e inglês
  language: "zh" | "en"
}
```

## Configuração do VMind

### LLM

O VMind requer invocação de LLM para geração inteligente de gráficos. Por padrão, ele usa a configuração `config.llm["default"]`.

### Configurações de Geração

As configurações principais incluem dimensões do gráfico, tema e método de geração:

### Método de Geração
Padrão: png. Atualmente suporta a seleção automática de `output_type` pelo LLM com base no contexto.

### Dimensões
As dimensões padrão não são especificadas. Para saída HTML, os gráficos preenchem a página inteira por padrão. Para saída PNG, o padrão é `1000*1000`.

### Tema
Tema padrão: `'light'`. O VChart suporta múltiplos temas. Consulte [Temas](https://www.visactor.io/vchart/guide/tutorial_docs/Theme/Theme_Extension).

## Teste

Atualmente, três tarefas de diferentes níveis de dificuldade são definidas para teste.

### Tarefa Simples de Geração de Gráfico

Forneça dados e requisitos específicos de geração de gráfico, teste os resultados, execute o comando:
```bash
python -m app.tool.chart_visualization.test.chart_demo
```
Os resultados devem estar localizados em `workspace\visualization`, envolvendo 9 resultados de gráficos diferentes.

### Tarefa Simples de Relatório de Dados

Forneça requisitos simples de análise de dados brutos, exigindo processamento simples dos dados, execute o comando:
```bash
python -m app.tool.chart_visualization.test.report_demo
```
Os resultados também estão localizados em `workspace\visualization`.
```
