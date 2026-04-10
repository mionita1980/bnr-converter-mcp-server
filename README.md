# BNR Converter MCP Server

MCP server for converting foreign currency amounts to RON (Romanian New Leu) using the rates published by BNR (Banca Nationala a Romaniei).

## Run

```bash
uvx bnr-converter
```

## Use from Claude Code

```json
"mcpServers": {
    "bnr-exchange": {
        "type": "stdio",
        "command": "uvx",
        "args": [
            "bnr-converter"
        ]
    }
}
```

### Sample Prompt 1

`Convert to RON a bill of 30 EUR from March 17, 2025`

Response:

```
30 EUR = 149.319 RON

  - BNR exchange rate used: 4.9773 RON/EUR
  - Rate date: March 14, 2025 (last published rate before the bill date)
```

### Sample Prompt 2

`Convert to RON a bill of 30 EUR from March 17, 2025, using the rate on the bill date`

Response:

```
30 EUR = 149.319 RON

  - BNR exchange rate used: 4.9773 RON/EUR
  - Rate date: March 17, 2025 (rate published on the bill date)
```

### Sample Prompt 3

`Convert to RON a bill of 30 EUR from March 17, 2025, using the rate before the bill date`

Response:

```
30 EUR = 149.304 RON

  - BNR exchange rate used: 4.9768 RON/EUR
  - Rate date: March 14, 2025 (last published rate before the bill date)
```

