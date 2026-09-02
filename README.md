# ChemDoc Miner

Power Dream / iLENE UV 原材料**对内销售目录**：从 TDS、SDS 和竞品对照表建成可查询的产品库。回答带出处，不编造指标。

## 能问什么

- `iLENE 700 是什么` / `Power Dream 有哪些环氧丙烯酸酯`
- `Allnex EB3700 对应谁` / `Photomer 4006` / `SR351`
- `低黄变、3D 打印用树脂` / `指甲胶、真空镀膜底涂`

对标来自内部对照表，**不是实验室等价证明**，需配方验证。

## 安装

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

系统需有 `tesseract`（仅用于少数扫描件 OCR）。已安装 Homebrew 时：`brew install tesseract`。

## 建库

```bash
python -m chemdoc_miner ingest
```

写入 `data/derived/chemdoc.db`，并生成 `data/derived/ingest_report.md`。

## 查询（Cursor Agent / 终端）

```bash
python -m chemdoc_miner ask "Allnex EB3700 对应什么"
python -m chemdoc_miner get HDDA
python -m chemdoc_miner eq Allnex EB3700
python -m chemdoc_miner xref Allnex EB3700
python -m chemdoc_miner recommend "低黄变 3D打印"
python -m chemdoc_miner list "Power Dream" --family ea
python -m chemdoc_miner stats
```

## 手机离线（单页 HTML）

统一离线页 **Finder + Catalog + Xref**：

```bash
python -m chemdoc_miner export-app-html
```

生成 `data/derived/ChemDoc.html`。AirDrop / 微信传文件到 iPhone，用 **Safari** 打开，可「添加到主屏幕」。

旧命令 `export-xref-html` / `export-products-html` / `export-finder-html` 也会生成同一文件。

项目内 skill：`.cursor/skills/chemdoc-miner/SKILL.md`。

## 销售 Web

```bash
python -m chemdoc_miner serve
```

打开 http://127.0.0.1:8765 。可搜索、对话、打开原始 TDS/SDS。仅本机，不要暴露到公网。

可选：设置 `OPENAI_API_KEY`（或 `CHEMDOC_LLM_API_KEY` + `CHEMDOC_LLM_BASE_URL`）后，对话会用模型组织中文回答，数字仍以库为准。

## 数据来源

| 目录 | 用途 |
|------|------|
| `doc/02 TDS-...` | iLENE 技术说明书（主数据） |
| `doc/01 SDS-...` | 安全说明书 |
| `doc/Competitive Landscape/...` | Offsets / ECR / PI / Additives 等价组（宽表一行一组） |

## 牌号编码（Power Dream）

- `2xxx` 聚氨酯丙烯酸酯
- `6xxx` 聚酯丙烯酸酯
- `7xxx` 环氧丙烯酸酯
- `8xxx` 氨改性
- `107x` 磷酸酯
- `381x` 分散剂
