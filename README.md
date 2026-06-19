# fortibleed-dataset-lookup

Public lists of domains and IPs associated with **FortiBleed** + a script to cross-check your own list (domains and/or IPs) against the datasets and find out if any of them show up.

## Data origin

The data was found on Mastodon, via the [#FortiBleed](https://mastodon.social/tags/FortiBleed) hashtag, from the following sources:

- https://blog.gayint.org/fortibleed.html
- http://owned.lab6.com/~gossi/research/public/fortibleed/some-fortibleed-ips.txt

The lists were cross-checked against other public lookup tools for validation:

- [Hudson Rock](https://www.hudsonrock.com/fortinet)
- [SOCRadar](https://socradar.io/free-tools/fortibleed)
- [Quimerax](https://tools.quimerax.com/fortibleed)

> ⚠️ **Defensive use.** This repository exists to help security teams check their **own exposure** (your domains / IPs / clients). Do not use it to target third parties.

## Contents

| File | Description |
| --- | --- |
| `fortibleed-public-dataset.txt` | Domain dataset — one per line (~21.8k entries). |
| `fortibleed-ips.txt` | IP dataset — one per line (~68.7k entries). |
| `fortibleed_lookup.py` | Cross-checking script. Python 3, no external dependencies. |

## Usage

```bash
# basic: list which of YOUR domains/IPs are in the datasets
python3 fortibleed_lookup.py my_targets.txt

# also count subdomains (e.g. vpn.acme.com matches acme.com)
python3 fortibleed_lookup.py my_targets.txt --subdomains

# only the HITs, and write the result to JSON
python3 fortibleed_lookup.py my_targets.txt -q --json result.json

# point to the FortiBleed datasets at another path (usually not needed)
python3 fortibleed_lookup.py my_targets.txt --domains-db dom.txt --ips-db ips.txt
```

`my_targets.txt` is **your** list — the positional argument, no flag. The
`--domains-db` / `--ips-db` flags only point to the FortiBleed datasets when
they are not next to the script (they are auto-detected otherwise).

The input is one entry per line, mixing domains and IPs freely. Each line is
automatically classified as an IP or a domain and compared against the matching
dataset. Blank lines and lines starting with `#` are ignored.

### Output

- Prints the domains and IPs from your list that **HIT** in the datasets.
- In `--subdomains` mode, it also shows which parent domain matched (`vpn.012.net (via 012.net)`).
- **Exit code** `1` when there is at least one HIT, `0` when the list is clean — chainable in CI/script pipelines.

## How matching works

Domains and IPs are normalized on both sides before comparing.

Domains:

- strip BOM, whitespace and comment lines (`#`);
- strip scheme (`http://`, `https://`), credentials (`user@`), path, query and port;
- strip `www.` and the trailing dot, and lowercase everything.

So `https://www.10ti.com.br/login` matches the entry `10ti.com.br`.

IPs:

- validated via `ipaddress` (IPv4/IPv6) and canonicalized;
- accepts IP with port (`1.0.128.10:443` matches `1.0.128.10`).

## Requirements

Python 3.7+. No dependencies beyond the standard library.

## Disclaimer

The datasets are provided for security research and defense purposes only. The author is not responsible for misuse.
