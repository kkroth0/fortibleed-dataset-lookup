# fortibleed-dataset-lookup

Listas públicas de domínios e IPs associados ao **FortiBleed** + um script para cruzar a sua própria lista (domínios e/ou IPs) contra os datasets e descobrir se algum aparece.

## Origem dos dados

Os dados foram localizados no Mastodon, pela hashtag [#FortiBleed](https://mastodon.social/tags/FortiBleed), a partir das seguintes fontes:

- https://blog.gayint.org/fortibleed.html
- http://owned.lab6.com/~gossi/research/public/fortibleed/some-fortibleed-ips.txt

As listas foram conferidas contra outras ferramentas de lookup públicas para validação:

- [Hudson Rock](https://www.hudsonrock.com/fortinet)
- [SOCRadar](https://socradar.io/free-tools/fortibleed)
- [Quimerax](https://tools.quimerax.com/fortibleed)

> ⚠️ **Uso defensivo.** Este repositório existe para ajudar times de segurança a verificar **exposição própria** (seus domínios / IPs / clientes). Não use para mirar terceiros.

## Conteúdo

| Arquivo | Descrição |
| --- | --- |
| `fortibleed-public-dataset.txt` | Dataset de domínios — um por linha (~21,8k entradas). |
| `fortibleed-ips.txt` | Dataset de IPs — um por linha (~68,7k entradas). |
| `fortibleed_lookup.py` | Script de cruzamento. Python 3, sem dependências externas. |

## Uso

```bash
# básico: lista quais dos SEUS domínios/IPs estão nos datasets
python3 fortibleed_lookup.py meus_alvos.txt

# também conta subdomínios (ex.: vpn.acme.com casa com acme.com)
python3 fortibleed_lookup.py meus_alvos.txt --subdomains

# só os HITs, e grava o resultado em JSON
python3 fortibleed_lookup.py meus_alvos.txt -q --json resultado.json

# apontar os datasets do FortiBleed em outro caminho (normalmente não precisa)
python3 fortibleed_lookup.py meus_alvos.txt --domains-db dom.txt --ips-db ips.txt
```

`meus_alvos.txt` é a **sua** lista — o argumento posicional, sem flag. As flags
`--domains-db` / `--ips-db` só servem pra apontar os datasets do FortiBleed
quando eles não estão ao lado do script (são detectados automaticamente).

A entrada é uma entrada por linha, misturando domínios e IPs livremente. Cada
linha é classificada automaticamente como IP ou domínio e comparada contra o
dataset correspondente. Linhas em branco e começadas com `#` são ignoradas.

### Saída

- Imprime os domínios e IPs da sua lista que **deram HIT** nos datasets.
- Em modo `--subdomains`, mostra também via qual domínio-pai casou (`vpn.012.net (via 012.net)`).
- **Exit code** `1` quando há pelo menos um HIT, `0` quando a lista está limpa — encadeável em pipelines de CI/scripts.

## Como o casamento funciona

Domínios e IPs são normalizados dos dois lados antes de comparar.

Domínios:

- remove BOM, espaços e linhas de comentário (`#`);
- remove esquema (`http://`, `https://`), credenciais (`user@`), caminho, query e porta;
- remove `www.` e o ponto final, e baixa tudo para minúsculo.

Então `https://www.10ti.com.br/login` casa com a entrada `10ti.com.br`.

IPs:

- valida via `ipaddress` (IPv4/IPv6) e canoniza;
- aceita IP com porta (`1.0.128.10:443` casa com `1.0.128.10`).

## Requisitos

Python 3.7+. Nenhuma dependência além da biblioteca padrão.

## Aviso legal

Os datasets são fornecidos apenas para fins de pesquisa e defesa de segurança. O autor não se responsabiliza por uso indevido.
