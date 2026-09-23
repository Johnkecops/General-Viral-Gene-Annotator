"""
General Viral Gene Annotator
=============================
An asynchronous, two-tiered AI-driven pipeline for viral genomic sequence
classification. Given a raw FASTA file, the pipeline scores the query sequence
against a panel of reference viral genomes (JEV, SARS-CoV-2, H5N1, Poliovirus,
HIV) using native k-mer alignment, then routes to TypeSafe System One (Tier 1)
and — for ambiguous calls — Gemini 3.8 Flash (Tier 2) for expert genomic analysis.

Example (JEV):
    fasta_file = "jev-gp2-gene.fa"   # Japanese Encephalitis Virus gp2 gene
    # Uncomment in main() and run:  python3 "jev sequence alignment.py"

Other supported pathogens:
    "HIV-gag-pol-gene.fna"            # HIV gag-pol gene
    "sars-cov-2-orf1ab-gene.fna"      # SARS-CoV-2 ORF1ab gene
    "Polio-PVgp1-gene.fna"            # Poliovirus PVgp1 gene
    "H5N1-NA-gene.fna"                # Influenza H5N1 NA gene

APIs required:
    TYPESAFE_API_KEY  — TypeSafe System One (Tier 1 screening)
    GEMINI_API_KEY    — Google Gemini 3.8 Flash (Tier 2 escalation)
"""
import asyncio
import os
from google import genai
from google.genai import types
# pyrefly: ignore [missing-import]
from typesafe_sdk import AsyncTypeSafeClient, Noul, Choice

# Initialize Clients
# TypeSafe System One Client
typesafe_client = AsyncTypeSafeClient(
    api_key=os.environ["TYPESAFE_API_KEY"]
)
# Initialize Gemini client (looks for GEMINI_API_KEY or GOOGLE_API_KEY environment variable)
gemini_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

CONFIDENCE_THRESHOLD = 0.85

# Reference viral panel files in the directory
REFERENCE_PANEL_FILES = {
    "hiv": "HIV-gag-pol-gene.fna",
    "sars_cov_2": "sars-cov-2-orf1ab-gene.fna",
    "influenza_h5n1": "H5N1-NA-gene.fna",
    "poliovirus": "Polio-PVgp1-gene.fna",
    "jev": "jev-gp2-gene.fa"
}

def parse_fasta(file_path: str) -> list[dict]:
    """Parses a standard multiline FASTA file directly in native Python without external dependencies."""
    records = []
    current_id, current_seq = None, []
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if current_id:
                    records.append({"id": current_id, "sequence": "".join(current_seq)})
                current_id = line[1:]
                current_seq = []
            else:
                current_seq.append(line)
        if current_id:
            records.append({"id": current_id, "sequence": "".join(current_seq)})
    return records

def load_reference_panel(base_dir: str = ".") -> dict[str, str]:
    """Loads viral reference sequences from local FASTA files without heavy bioinformatics frameworks."""
    references = {}
    for virus, filename in REFERENCE_PANEL_FILES.items():
        filepath = os.path.join(base_dir, filename)
        if os.path.exists(filepath):
            records = parse_fasta(filepath)
            if records:
                references[virus] = records[0]["sequence"].upper()
    return references

def compute_kmer_alignment(query_seq: str, ref_seq: str, k: int = 15) -> float:
    """
    Performs fast, native Python k-mer sequence alignment / similarity scoring.
    Returns the proportion of unique k-mers in the query that match the reference genome.
    """
    query_seq = query_seq.upper()
    ref_seq = ref_seq.upper()
    if len(query_seq) < k or len(ref_seq) < k:
        return 0.0
    query_kmers = set(query_seq[i:i+k] for i in range(len(query_seq) - k + 1))
    ref_kmers = set(ref_seq[i:i+k] for i in range(len(ref_seq) - k + 1))
    if not query_kmers:
        return 0.0
    common = query_kmers.intersection(ref_kmers)
    return len(common) / len(query_kmers)

async def triage_fasta_record(record: dict, references: dict[str, str]):
    sample_id = record["id"]
    sequence_data = record["sequence"]
    
    # 1. Native Sequence Alignment against local viral reference panel
    alignment_scores = {
        virus: compute_kmer_alignment(sequence_data, ref_seq)
        for virus, ref_seq in references.items()
    }
    top_aligned_virus = max(alignment_scores, key=alignment_scores.get) if alignment_scores else "none"
    max_align_score = alignment_scores.get(top_aligned_virus, 0.0)
    
    align_summary_str = ", ".join([f"{v.upper()}: {s*100:.1f}%" for v, s in alignment_scores.items()])
    
    # Assemble bio_state incorporating the biological sequence alignment profile
    bio_state = f"""
    [Sample Identifier]
    FASTA Header: {sample_id}
    
    [Biological Sequence Alignment Profile against Reference Panel]
    Top Alignment Hit: {top_aligned_virus.upper()} ({max_align_score*100:.1f}% k-mer match)
    All Reference Alignments: {align_summary_str}
    
    [Genomic Sequence Data]
    Length: {len(sequence_data)} bp
    Sequence Preview: {sequence_data[:300]}...
    """
    
    try:
        # Evaluate via TypeSafe System One model
        response = await typesafe_client.system_one(
            state=bio_state,
            questions={
                "viral_classification": Choice(
                    instructions=(
                        "Classify which viral pathogen this genomic sequence belongs to based on the "
                        "biological sequence alignment profile, sequence characteristics, and homology:"
                    ),
                    criteria={
                        "jev": "Japanese Encephalitis Virus (Flaviviridae)",
                        "sars_cov_2": "SARS-CoV-2 Coronavirus (Coronaviridae)",
                        "influenza_h5n1": "Influenza A virus subtype H5N1 (Orthomyxoviridae)",
                        "poliovirus": "Poliovirus (Picornaviridae)",
                        "hiv": "Human Immunodeficiency Virus (Retroviridae gag-pol gene)",
                        "none": "None of the above / Non-viral / Synthetic artifact"
                    }
                )
            }
        )
        
        answer = response.answers["viral_classification"]
        top_hit = answer.choice
        confidence = answer.confidence
        probabilities = answer.probabilities
        
        if confidence >= CONFIDENCE_THRESHOLD:
            return {
                "id": sample_id,
                "top_hit": top_hit.upper(),
                "confidence": confidence,
                "probabilities": probabilities,
                "alignment_scores": alignment_scores,
                "status": "Auto-Processed"
            }
            
        # 2. Escalation path using Gemini 3.8 Flash (Google GenAI Asynchronous Client)
        print(f"[⚠️ Escalating] Sample {sample_id} dropped below threshold (confidence: {confidence*100:.1f}%). Triggering Gemini 3.8 Flash analysis...")
        
        try:
            heavy_response = await gemini_client.aio.models.generate_content(
                model="gemini-3.8-flash",
                contents=(
                    f"Analyze this sequence variant against target viral pathogens (JEV, SARS-CoV-2, H5N1, Poliovirus, HIV) "
                    f"for potential homology, recombination, or anomalies. Consider the alignment profile:\n{bio_state}"
                ),
                config=types.GenerateContentConfig(
                    system_instruction="You are an advanced viral genomics expert specializing in human and zoonotic viral pathogens (Flaviviruses, Coronaviruses, Orthomyxoviruses, Picornaviruses, Retroviruses).",
                    max_output_tokens=1500,
                ),
            )
            analysis_text = heavy_response.text
            escalation_status = "Escalated to Gemini"
        except Exception as gemini_err:
            analysis_text = f"Gemini escalation unavailable ({gemini_err}). Fallback to Alignment/Tier 1 candidate: {top_hit.upper()}."
            escalation_status = "Tier 1 Fallback (Gemini Unreachable)"
            
        return {
            "id": sample_id,
            "top_hit": top_hit.upper(),
            "confidence": confidence,
            "probabilities": probabilities,
            "alignment_scores": alignment_scores,
            "status": escalation_status,
            "analysis": analysis_text
        }
        
    except Exception as e:
        return {"id": sample_id, "status": "Error", "error": str(e)}

async def main():
    # Active FASTA query file
    # fasta_file = "jev_samples.fasta"
    # fasta_file = "HIV-gag-pol-gene.fna"
    # fasta_file = "sars-cov-2-orf1ab-gene.fna"
    # fasta_file = "Polio-PVgp1-gene.fna"
    # fasta_file = "H5N1-NA-gene.fna"
    # fasta_file = "jev-gp2-gene.fa"
    fasta_file = "gene.fasta"
    
    script_dir = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else "."
    fasta_path = os.path.join(script_dir, fasta_file) if not os.path.isabs(fasta_file) else fasta_file
    
    if not os.path.exists(fasta_path):
        print(f"Error: {fasta_path} not found.")
        return
        
    records = parse_fasta(fasta_path)
    print(f"Loaded {len(records)} sequence(s) from raw FASTA file ({fasta_file}).")
    
    # Load local reference panel
    references = load_reference_panel(script_dir)
    print(f"Loaded {len(references)} viral reference genome(s): {', '.join([k.upper() for k in references.keys()])}")
    
    tasks = [triage_fasta_record(rec, references) for rec in records]
    results = await asyncio.gather(*tasks)
        
    print("\n=== General Viral Gene Annotator — Sequence Classification Summary ===")
    for res in results:
        err_info = f" | Error: {res['error']}" if "error" in res else ""
        top_hit_str = res.get("top_hit", "PENDING")
        print(f"Record: {res['id']:<33} | Action: {res['status']:<14} | Top Hit: {top_hit_str:<12} | Confidence: {res.get('confidence', 0.0)*100:.1f}%{err_info}")
        if "alignment_scores" in res and res["alignment_scores"]:
            align_str = ", ".join([f"{k.upper()}: {v*100:.1f}%" for k, v in res["alignment_scores"].items()])
            print(f"   ├─ Reference Alignment Match: {align_str}")
        if "probabilities" in res and res["probabilities"]:
            prob_str = ", ".join([f"{k}: {v*100:.1f}%" for k, v in res["probabilities"].items()])
            print(f"   └─ TypeSafe Viral Classification Probabilities: {prob_str}")

if __name__ == "__main__":
    asyncio.run(main())
