---
name: deep-research-second-phase
description: >-
  Fase 2 de uma Deep Research técnica: pega o resultado bruto da pesquisa que já
  está no contexto (PDF, DOCX, Markdown, texto colado ou arquivos indicados) e o
  reescreve no Deep Research Document oficial de 16 seções, em Markdown, preservando
  100% das informações, frases, dados, exemplos e referências, sem resumir nada.
  Use sempre que o usuário quiser formatar, reorganizar, padronizar, reestruturar ou
  converter o resultado de uma deep research ou pesquisa técnica no modelo Deep
  Research Document, nas 16 seções ou em um documento de pesquisa oficial, inclusive
  com frases como "fase 2 da deep research", "organiza essa pesquisa no template",
  "transforma esse PDF da pesquisa no documento padrão" ou "gera o Deep Research
  Document", mesmo que ele não cite o nome da skill. Não use para resumir uma
  pesquisa, para montar o briefing antes da pesquisa (isso é a fase 1) nem para
  executar a pesquisa em si.
---

# Deep Research — Fase 2: Deep Research Document

A pesquisa já foi feita. Esta fase pega o material que a ferramenta de pesquisa produziu e o reescreve no modelo oficial de **Deep Research Document**, com 16 seções fixas.

A regra central é **fidelidade total**: 100% das informações, frases, dados, exemplos e explicações do material original precisam estar no documento final. Quem ler o documento não vai ter o original em mãos, então qualquer coisa omitida, condensada ou generalizada se perde de vez. Quando tiver dúvida entre deixar o texto mais enxuto e manter tudo, mantenha tudo. Um documento longo e completo é o resultado esperado; um documento elegante com lacunas é uma falha.

## Seu papel

Você é um editor técnico e arquiteto de documentação. Seu trabalho é reorganizar e dar clareza, não decidir o que é importante. Você não acrescenta fatos, não corta conteúdo e não muda o sentido do que a pesquisa diz.

Este trabalho exige raciocínio cuidadoso: pense passo a passo (ultrathink) no inventário e na verificação, que são as etapas que garantem os 100%.

## 1. Localize e leia todo o material

O material da pesquisa já está no contexto; não peça para o usuário colar nada. Ele pode estar em:

- anexos da conversa (PDF, DOCX, MD, TXT);
- texto colado em mensagens anteriores;
- arquivos que o usuário indicou por caminho (por exemplo, `@docs/pesquisa.pdf`).

Leia **tudo**, do início ao fim, incluindo todos os documentos quando houver mais de um. Em PDFs longos, leia todas as páginas, em partes se a ferramenta exigir. Não comece a escrever com base em uma leitura parcial: conteúdo que você não leu é conteúdo que vai faltar.

Só pergunte ao usuário se não encontrar material de pesquisa nenhum. Nesse caso, pergunte onde ele está.

Ao ler PDFs, separe o que é conteúdo do que é artefato de paginação. Cabeçalhos e rodapés repetidos, números de página e marcações como "Página 3" não são conteúdo e não entram no documento. Todo o resto entra.

## 2. Faça o inventário antes de escrever

A única forma confiável de garantir 100% é saber o que é 100% antes de começar. Quebre o material em unidades e atribua cada uma a uma seção de destino:

- cada parágrafo;
- cada item de lista;
- cada tabela (inteira, com todas as linhas e colunas);
- cada bloco de código, fórmula ou exemplo de configuração;
- cada figura ou diagrama (legenda e a informação que ele transmite);
- cada citação, dado numérico e referência bibliográfica.

Em material longo, escreva esse inventário em um arquivo de trabalho fora do documento final (por exemplo, numa pasta temporária), com uma linha por unidade: identificador, primeiras palavras e seção de destino. Esse arquivo é a sua lista de conferência na etapa 4.

Use esta tabela como guia de destino:

| Conteúdo no material original | Seção de destino |
|---|---|
| Introdução, problema, motivação, resumo executivo, visão geral | 1 |
| Definições, conceitos, princípios, terminologia, teoria | 2 |
| Estado da arte, abordagens conhecidas, padrões, comparação entre soluções | 3 |
| Topologias, camadas, fluxos de dados, diagramas de arquitetura | 4 |
| Algoritmos, estratégias, mecanismos, trade-offs entre eles | 5 |
| Ferramentas, bibliotecas, protocolos, frameworks, comparação de maturidade | 6 |
| Recomendações, boas práticas, anti-patterns, lições aprendidas | 7 |
| Métricas, KPIs, benchmarks, critérios e métodos de avaliação | 8 |
| Estudos de caso, empresas, exemplos de uso real | 9 |
| Riscos, limitações, pontos de falha, mitigações | 10 |
| Segurança, conformidade, privacidade, confiabilidade, versionamento | 11 |
| Tendências, pesquisas emergentes, evolução | 12 |
| Integração com outros sistemas, times, processos e camadas | 13 |
| Decisões recomendadas, alternativas, critérios de escolha | 14 |
| Conclusões, recomendações finais, roadmap, como aplicar | 15 |
| Referências, bibliografia, links, fontes | 16 |

Casos que costumam gerar perda:

- **O resumo executivo do original também é conteúdo.** Ele não foi escrito por você, então mantê-lo não é "resumir". Coloque-o na seção 1 (por exemplo, como `### Visão geral`), mesmo que repita pontos detalhados depois.
- **Conteúdo que serve a duas seções** pode e deve ser duplicado. Uma tabela comparativa de ferramentas pode aparecer na seção 6 e ter os trade-offs retomados na seção 5. Duplicar é melhor do que escolher uma seção e deixar a outra sem o contexto.
- **Conteúdo que não se encaixa claramente** vai para a seção mais relacionada, com "(conteúdo contextual adicional)" logo após o trecho ou o subtítulo.
- **A conclusão do original** costuma se dividir entre as seções 14 e 15. Garanta que cada frase dela tenha um destino.

## 3. Escreva o documento

Use exatamente este esqueleto. Os nomes das 16 seções, a numeração e a ordem são fixos. O texto entre colchetes indica o que preencher:

```markdown
# Deep Research Document

**Título:** [tema técnico da pesquisa]

**Versão:** 1.0

**Data:** [data atual, DD/MM/AAAA]

**Responsável:** [autor indicado pelo usuário ou pelo material; se não houver, a ferramenta que gerou a pesquisa, se identificada; senão, "IA"]

## 1. Contexto e Motivação

## 2. Fundamentos e Conceitos-Chave

## 3. Panorama e Abordagens Existentes

## 4. Arquiteturas e Modelos de Aplicação

## 5. Estratégias, Algoritmos e Mecanismos

## 6. Tecnologias, Frameworks e Ferramentas

## 7. Boas Práticas e Diretrizes Técnicas

## 8. Métricas e Critérios de Avaliação

## 9. Casos de Uso e Aplicações Reais

## 10. Riscos, Desafios e Limitações

## 11. Considerações de Segurança, Confiabilidade e Governança

## 12. Tendências e Evolução Futura

## 13. Impactos e Relações com o Ecossistema

## 14. Decisões e Oportunidades Técnicas (ADRs Candidatos)

## 15. Próximos Passos e Aplicação Prática

## 16. Referências e Leituras Recomendadas
```

O que cada seção deve conter:

1. **Contexto e Motivação:** o problema técnico, a oportunidade ou a motivação que originou a pesquisa, incluindo relevância e impacto.
2. **Fundamentos e Conceitos-Chave:** princípios, teorias, modelos ou terminologias essenciais para compreender o tema.
3. **Panorama e Abordagens Existentes:** as abordagens predominantes, soluções conhecidas, padrões ou frameworks relacionados ao problema.
4. **Arquiteturas e Modelos de Aplicação:** como o tema é aplicado em nível arquitetural, com topologias, camadas e fluxos de dados típicos.
5. **Estratégias, Algoritmos e Mecanismos:** as principais estratégias, algoritmos e mecanismos que endereçam o problema, com diferenças e trade-offs.
6. **Tecnologias, Frameworks e Ferramentas:** tecnologias, bibliotecas, protocolos ou frameworks relevantes, com comparação de maturidade e aplicabilidade.
7. **Boas Práticas e Diretrizes Técnicas:** recomendações de implementação, anti-patterns, práticas de governança e lições de engenharia.
8. **Métricas e Critérios de Avaliação:** como medir o sucesso técnico ou operacional, com métricas e métodos de avaliação.
9. **Casos de Uso e Aplicações Reais:** exemplos de aplicação prática, estudos de caso ou referências de uso do tema no mercado.
10. **Riscos, Desafios e Limitações:** riscos, limitações técnicas, pontos de falha conhecidos e estratégias de mitigação.
11. **Considerações de Segurança, Confiabilidade e Governança:** segurança, conformidade, privacidade, confiabilidade e versionamento.
12. **Tendências e Evolução Futura:** tendências, inovações ou pesquisas emergentes relacionadas ao tema.
13. **Impactos e Relações com o Ecossistema:** como o tema interage com outros sistemas, times, processos ou camadas de arquitetura.
14. **Decisões e Oportunidades Técnicas (ADRs Candidatos):** decisões técnicas ou arquiteturais derivadas da pesquisa, com critérios de escolha e alternativas rejeitadas.
15. **Próximos Passos e Aplicação Prática:** como aplicar os aprendizados em produtos, sistemas, pipelines ou processos futuros.
16. **Referências e Leituras Recomendadas:** todas as fontes usadas pela pesquisa: artigos, papers, RFCs, whitepapers, documentações e materiais técnicos.

Essas descrições servem para você decidir o que vai em cada seção. Não as copie para o documento: abaixo de cada título vem o conteúdo da pesquisa.

### Regras de reescrita

- **Só clareza e coerência.** Você pode reordenar frases, juntar parágrafos que tratam do mesmo ponto, criar frases de transição e corrigir erros de linguagem. Não pode trocar um dado por uma generalização ("reduziu a latência de 800 ms para 120 ms" não vira "reduziu bastante a latência"), apagar exemplos, ressalvas ("em geral", "segundo o autor X", "em cenários com alta concorrência") ou nuances.
- **Nada de resumo.** Não escreva "em resumo", "em síntese" nem parágrafos que condensam o que vem depois no lugar do conteúdo. Uma frase de abertura que conecta a seção ao resto é aceitável, desde que o conteúdo completo venha em seguida.
- **Números, nomes e termos exatamente como no original:** valores, unidades, versões, nomes de produtos, empresas, autores e siglas.
- **Preserve a forma do conteúdo estruturado:** tabelas continuam tabelas, com todas as linhas e colunas; código e configurações continuam em blocos de código com a linguagem indicada; listas continuam listas; citações literais continuam citações.
- **Figuras e diagramas:** mantenha a legenda e descreva em texto a informação que a figura transmite, quando ela for legível no material.
- **Idioma:** escreva o conteúdo no idioma do material original e mantenha os nomes das seções exatamente como no esqueleto. Só traduza se o usuário pedir, porque traduzir é uma reescrita que facilita perdas.

### Formatação

- `#` só para "Deep Research Document"; `##` só para as 16 seções; `###` e `####` para subseções dentro delas. Títulos do material original geralmente viram bons subtítulos `###`.
- Use tabelas, listas, negrito e blocos de código onde ajudarem a leitura, como num documento técnico bem diagramado.
- Não divida o documento em páginas e não escreva "Página 1", "Página 2" nem equivalentes.

### Seções sem material

As 16 seções aparecem sempre, mesmo quando o material não trata de algum aspecto.

- As seções 14 e 15 são derivadas por natureza: monte-as a partir das decisões, trade-offs, recomendações e conclusões que a pesquisa já contém, citando os critérios e alternativas que ela discute.
- Nas demais, se nada do material couber, escreva uma frase dizendo que a pesquisa não aborda aquele aspecto. Não invente fatos, números, casos ou fontes para preencher a seção.

### Sem referências ao material de origem

O documento precisa se sustentar sozinho, como se o original não existisse. Não escreva "segundo o documento anexado", "conforme o PDF", "como visto no material" nem indique páginas ou trechos do original.

Isso não vale para as fontes da pesquisa. Autores, artigos, RFCs e URLs que a pesquisa cita fazem parte do conteúdo: mantenha as citações no texto e reúna todas as fontes, com todos os dados disponíveis (título, autor, data, URL), na seção 16.

Marcadores internos da ferramenta de pesquisa que não carregam informação legível (como `citeturn0search3`, `【12†source】` ou `[cite: 4]`) não são conteúdo. Se apontarem para uma fonte identificável, substitua pela referência; se não, remova.

## 4. Verifique a cobertura

Antes de entregar, confira que tudo do inventário está no documento. Percorra a lista unidade por unidade e localize cada uma no texto final. Qualquer ausência deve ser corrigida no documento antes da entrega, não apenas anotada.

Se puder executar Python, rode também o verificador incluído nesta skill. Ele compara itens objetivos que não deveriam sumir numa reescrita (URLs, números, termos técnicos e código) e confere o cabeçalho, os nomes e a ordem das 16 seções, além de marcações de página e referências ao material de origem:

```bash
python scripts/check_coverage.py --output <documento.md> --source <material.md> [--source <outro.md>]
```

O caminho do script é relativo à pasta desta skill. Use `python3` ou `uv run python` se `python` não estiver disponível. Para fontes em PDF ou DOCX, salve antes o texto extraído em um arquivo `.txt` ou `.md` temporário e passe esse arquivo.

Cada item listado pelo script precisa ser conferido. Pode ser uma perda real (corrija e rode de novo) ou só uma mudança de forma, como "1.000" escrito por extenso. O script também compara a contagem de palavras: reorganizar sem resumir normalmente mantém ou aumenta o tamanho, então um documento bem menor que a origem indica conteúdo condensado. O script não substitui a conferência pelo inventário, porque não detecta uma explicação que foi parafraseada pela metade.

## 5. Entregue

Entregue só o Deep Research Document, em Markdown puro, sem introdução, comentários ou relatório da conversão.

- **Se você puder gravar arquivos:** salve o documento como `.md` no local que o usuário indicar. Se ele não indicar, salve na mesma pasta do material de origem, com um nome derivado do título (por exemplo, `deep-research-outbox-pattern.md`). Na conversa, responda apenas com o caminho do arquivo.
- **Se não puder:** escreva o documento diretamente na resposta, sem envolvê-lo em um bloco de código (os blocos de código internos quebrariam o bloco externo).

### Material grande: geração em partes

Quando o documento completo não couber em uma única resposta, gere em partes. Você pode dividir assim, e só nesse caso fala com o usuário além de entregar o Markdown:

1. Faça o inventário do material **inteiro** antes da primeira parte, para que nada destinado a seções posteriores se perca entre as partes.
2. Defina os blocos de seções pelo volume de conteúdo atribuído a cada uma (por exemplo, 1 a 3, depois 4 a 7, e assim por diante).
3. Avise em uma frase antes da primeira parte, por exemplo: "Como o material é extenso, vou gerar o documento em partes, começando pelas seções 1 a 3."
4. Entregue a parte. O cabeçalho (título, versão, data e responsável) aparece só na primeira.
5. Ao final de cada parte, pergunte se o usuário quer continuar, por exemplo: "Deseja que eu continue agora com as seções 4 a 7?"
6. Antes de entregar cada parte, confira no inventário as unidades atribuídas às seções dela. Na última parte, confira o inventário inteiro.

Se estiver gravando em arquivo, não precisa parar para perguntar: escreva o arquivo seção por seção, em gravações sucessivas, até completar as 16, e verifique a cobertura no arquivo final.
