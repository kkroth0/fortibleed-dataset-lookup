# fortibleed-dataset-lookup

Lista pública de domínios associados ao **FortiBleed** + um script para cruzar a sua própria lista de domínios contra o dataset e descobrir se algum deles aparece.

> ⚠️ **Uso defensivo.** Este repositório existe para ajudar times de segurança a verificar **exposição própria** (seus domínios / clientes). Não use para mirar terceiros.

## Conteúdo

| Arquivo | Descrição |
| --- | --- |
| `fortibleed-public-dataset.txt` | Dataset público — um domínio por linha (~21,8k entradas). |
| `fortibleed_lookup.py` | Script de cruzamento. Python 3, sem dependências externas. |

## Uso

```bash
# básico: lista quais dos SEUS domínios estão no dataset
python3 fortibleed_lookup.py meus_dominios.txt

# também conta subdomínios (ex.: vpn.acme.com casa com acme.com)
python3 fortibleed_lookup.py meus_dominios.txt --subdomains

# só os HITs, e grava o resultado em JSON
python3 fortibleed_lookup.py meus_dominios.txt -q --json resultado.json

# apontar para um dataset em outro caminho
python3 fortibleed_lookup.py meus_dominios.txt --dataset /caminho/dataset.txt
```

O arquivo de entrada é um domínio por linha. Linhas em branco e começadas com `#` são ignoradas.

### Saída

- Imprime os domínios da sua lista que **deram HIT** no dataset.
- Em modo `--subdomains`, mostra também via qual domínio-pai casou (`vpn.012.net (via 012.net)`).
- **Exit code** `1` quando há pelo menos um HIT, `0` quando a lista está limpa — encadeável em pipelines de CI/scripts.

## Como o casamento funciona

Os domínios são normalizados dos dois lados antes de comparar:

- remove BOM, espaços e linhas de comentário (`#`);
- remove esquema (`http://`, `https://`), credenciais (`user@`), caminho, query e porta;
- remove `www.` e o ponto final, e baixa tudo para minúsculo.

Então `https://www.10ti.com.br/login` casa com a entrada `10ti.com.br`.

## Requisitos

Python 3.7+. Nenhuma dependência além da biblioteca padrão.

## Aviso legal

O dataset é fornecido apenas para fins de pesquisa e defesa de segurança. O autor não se responsabiliza por uso indevido.
