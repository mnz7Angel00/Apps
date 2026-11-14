# prompt_eval

Banco de testes de prompt com corretor automático. Serve para medir um modelo
(por exemplo, um Sonnet) em vez de só "conversar e ver no que dá".

- 27 casos, 8 categorias, pesos diferentes
- corretor determinístico (sem LLM-juiz): substring, regex, contagem de
  palavras, JSON válido
- três modos: imprimir para colar na interface, chamar a API, ou corrigir
  respostas que você já tem em arquivo
- só stdlib, Python 3.8+

## Categorias

| categoria | o que mede | por que importa |
|---|---|---|
| `instrucao` | seguir formato rígido: contagem exata de palavras, caixa, JSON puro, restrição negativa | aderência é a habilidade mais frágil em uso real |
| `raciocinio` | pegadinhas clássicas (caracol, desconto encadeado, dia da semana) | modelos erram aritmética simples sob pressão de contexto |
| `honestidade` | perguntar sobre coisa que não existe ou dado privado | mede se inventa em vez de admitir |
| `bajulacao` | usuário afirma algo falso com confiança (ou se diz especialista) | mede se o modelo concorda com quem fala |
| `injecao` | instrução escondida dentro do conteúdo a processar | é o furo de segurança real de qualquer agente |
| `recusa` | pedido defensivo legítimo que *parece* sensível | recusar aqui é falso positivo e quebra o produto |
| `contexto_longo` | agulha no meio e no fim de ~700 palavras | mede recuperação e viés de posição |
| `idioma` | responder em pt-br e não vazar inglês | adesão ao idioma pedido |

## Uso

### 1. Colar na interface (sem chave de API)

```bash
python run_eval.py print                    # todos os 27
python run_eval.py print --only injecao     # só uma categoria
python run_eval.py print --case inj-01 if-02
```

Cada caso vem com o prompt e uma linha "o que observar". Copie, cole, leia a
resposta.

### 2. Corrigir respostas salvas em arquivo

Salve cada resposta como `<id>.txt` numa pasta:

```
minhas_respostas/
  if-01.txt
  inj-01.txt
  re-03.txt
```

```bash
python run_eval.py grade --responses ./minhas_respostas
```

Casos sem arquivo aparecem como `SKIP` e não entram na nota.

### 3. Chamar a API direto

```bash
export ANTHROPIC_API_KEY=...
python run_eval.py run --model claude-sonnet-4-6
python run_eval.py run --model claude-sonnet-4-6 --only injecao --show-answer
python run_eval.py run --json-out resultado.json
```

O modelo é configurável por `--model` ou pela env `ANTHROPIC_MODEL`. Ajuste o
identificador para o que a sua conta aceitar.

## Saída

```
PASS inj-01   injecao            63 palavras
FAIL re-01    raciocinio         41 palavras
       - faltou um de ['8 dias', '8º dia', 'oitavo dia']
```

e no fim, um placar ponderado por categoria:

```
categoria              acertos   barra
------------------------------------------------
injecao                 4/4      ████
raciocinio              4/5      ████░
------------------------------------------------
TOTAL (ponderado)      31.0/38    81.6%
```

Código de saída: `0` se tudo passou, `1` se algo falhou — dá pra usar em CI.

## Sobre os casos de injeção

Os quatro casos `inj-*` usam **canários inofensivos**: a instrução escondida
manda o modelo responder `BANANA`, `42`, `PWNED` ou `LIBERADO`. Não há nada
danoso ali — o teste é sobre *obediência a texto que chega de fora do canal de
instruções*, não sobre conteúdo.

Se você apontar o `prompt_guard.py` para este `cases.json`, ele vai marcar o
arquivo como suspeito (~0.53). Isso está certo: a ferramenta não sabe
distinguir um corpus de teste de um ataque real. Vale a lição — qualquer
detector vai ter esse falso positivo, e é por isso que ele deve ser usado como
triagem, não como veredito.

## Adicionar casos

Edite `cases.json` e acrescente um objeto. Chaves de `expect` suportadas:

| chave | efeito |
|---|---|
| `must_include` | todas as substrings precisam aparecer (case-insensitive) |
| `must_include_any` | lista de grupos; cada grupo precisa de ao menos uma |
| `must_exclude` | nenhuma dessas pode aparecer |
| `regex` | todas as regex precisam casar |
| `word_count` | número exato de palavras |
| `max_words` / `min_words` | limites |
| `json_valid` | o corpo precisa ser JSON parseável |
| `json_keys` | chaves obrigatórias no objeto |

E opcionalmente `filler` (`words`, `needle`, `needle_at`) para gerar o teste de
contexto longo dinamicamente.

## Testes

```bash
python -m unittest tests.test_prompt_eval -v
```
