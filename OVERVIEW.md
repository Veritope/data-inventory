# Making sense of the inventory

This is the reading of the catalog: what we actually have, what to use first for
each program, how the licensing lands for a for-profit company, and where the real
gaps are. The numbers come from [`stats.json`](stats.json); the per-dataset detail
is in [`index.json`](index.json). For programmatic use, start with [`AGENTS.md`](AGENTS.md).

The catalog holds **576 datasets** across 12 categories. 509 are open and
automatable. It was assembled by reading the primary literature — the major
reviews, benchmark papers, and resource papers — and extracting the datasets and
accessions they released, then merging and deduplicating.

## How to read a program's data

Each dataset is tagged with the Veritope program(s) it serves. The counts below
are generous (a structure corpus serves both presentation and design), so the
"start here" lists are hand-picked anchors, not the full tag set.

### Presentation — which peptides a tumor displays
The spine is experimental immunopeptidomics (peptides eluted from MHC and read by
mass spec), not predicted binding.
- **`iedb`**, **`cedar`** — curated epitopes and cancer epitopes (CC BY; bulk + API).
- **`hla-ligand-atlas`** — benign/normal-tissue immunopeptidome, the self-filter (CC0).
- **`systemhc-atlas`**, **`sarkizova-2020-monoallelic`**, **`abelin-2017-monoallelic`** — mono-allelic ligandomes that anchor allele-specific motifs.
- **`mhcflurry2-training-data`**, **`bigmhc-training-data`**, **`netmhcpan41-training-set`** — ready-made model training/eval sets (mind licenses; see below).
- Canine: **`canine-dla88-immunopeptidome-atlas`**, **`pxd074485`**, **`canine-dla-immunopeptidomics`** — the entire public dog presentation layer, DLA-88 only.

### Recognition — which displayed peptides a T cell engages
- **`vdjdb`**, **`mcpas-tcr`**, **`iedb-tcr`** — curated TCR–epitope pairs (note `vdjdb` is CC BY-ND).
- **`10x-tcr-pmhc-dextramer`** — large paired specific/negative TCRs (CC BY, clean).
- **`dash-2017-tcrdist`**, **`glanville-2017-gliph`** — the foundational paired-specificity sets.
- **`tchard`** — aggregated TCR–pMHC (non-commercial).
- Structure: **`stcrdab`**, **`tcr3d`**, **`atlas-tcr-pmhc`** (TCR–pMHC complexes + affinity).
- Canine: **`canine-sctcr-2024-prjna742469`** — the only purpose-built dog TCR set; no epitope labels.

### Design — engineering recognition against a verified target
- **`rcsb-pdb`** (CC0) and **`alphafold-db`** (CC BY) — experimental + predicted structure ground truth.
- **`uniref`**, **`bfd`**, **`esm-atlas`**, **`openproteinset`** — sequence/structure corpora for pretraining a representation.
- **`stcrdab`**, **`tcr3d`**, **`hla3db`**, **`pandora-templates`** — pMHC/TCR–pMHC structural sets to build against.
- **`skempi2`**, **`ab-bind`**, **`ppb-affinity`** — binding-affinity-on-mutation data for scoring designs.
- **`oas`** — >1B antibody sequences, the binder-design precedent (CC BY).

### Comparative (canine) — the starting setting
- **`icdc`** (and its studies), **`dog10k`**, **`canfam31`**/**`uu-cfam-gsd`**, **`ipd-mhc`** — reference and cohort backbone.
- **`canine-dla88-immunopeptidome-atlas`**, **`pxd074485`** — the key finding: dog tumor peptides, with evidence that a sizeable fraction match human HLA peptides.
- **`geo-gse238110-canine-osa-rnaseq`**, **`canine-sctcr-2024-prjna742469`**, **`catch-histology`** — tumor expression, TCR, and pathology.

## Licensing, for a for-profit company
183 datasets are clearly commercial-use-OK; 21 are restricted; the rest are
unverified (treat as "check before commercial use"). Query the `commercial_use`
field before ingesting.

- **Clean anchors (CC0 / CC BY / MIT / Apache):** PDB, AlphaFold DB, IEDB, CEDAR, MHCflurry, HLA Ligand Atlas, the 10x dextramer data, OAS, UniRef.
- **Restricted — do not train/redistribute commercially without checking:** `vdjdb` (CC BY-ND), `tchard` (NC), `mhc-motif-atlas` (NC), `peptideatlas` (NC), `netmhcpan`/`mixmhcpred` (academic / separate commercial license), KEGG (paid), CIBERSORT/LM22 (NC), several spatial-pathology sets (PANDA, PanNuke, TIGER, BACH).

## Data volume
Measured at **~11.0 PB**, but that figure is dominated by one raw cryo-EM archive
(`empiar`). Only 57 datasets publish a size; the large controlled-access genomics
cohorts (TCGA/GDC et al., themselves petabyte-scale) do not, so this is a lower
bound. See the README snapshot for the breakdown.

## The gaps — where our own data generation matters most
The crawl confirmed these are not oversights in the catalog; the data does not exist publicly.
1. **Canine presentation is DLA-88 only.** No other class I locus, no class II at scale. One tumor immunopeptidome atlas, period.
2. **No epitope-labelled canine TCRs.** There is no dog VDJdb/McPAS; only unlabeled repertoires and one small paired single-cell set.
3. **No DLA allele-frequency or breed-level typing resource**, and no IMGT-grade canine germline V(D)J for the recognition arm.
4. **Reference fragmentation:** canine data is split across CanFam3.1 / CanFam4 / ROS_Cfam / Tasha assemblies; a pipeline must pin one and lift over.

These four are the strongest case for Veritope generating its own canine presentation
and recognition data — the models have a rich human substrate to learn from and a
thin canine one to be measured against.
