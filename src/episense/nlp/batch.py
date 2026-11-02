"""
Batch Processing Engine for EpiSense NLP Pipeline.
Processes document benchmarks and surveillance corpora without modifying source data.
"""

import json
import time
from pathlib import Path
from typing import List, Optional, Union
from uuid import uuid4

from episense.schemas.nlp import BatchProcessingReport, NLPOutput
from episense.nlp.pipeline import NLPPipeline
from episense.logging import get_logger

logger = get_logger("nlp.batch")


class BatchRunner:
    """
    Executes batch NLP processing across benchmark and background corpora
    with error isolation and execution reporting.
    """

    def __init__(self, pipeline: Optional[NLPPipeline] = None, output_base_dir: str = "data/processed/nlp_runs"):
        self.pipeline = pipeline or NLPPipeline()
        self.output_base_dir = Path(output_base_dir)

    def process_corpus_file(
        self, corpus_path: Union[str, Path], run_name: Optional[str] = None
    ) -> tuple[BatchProcessingReport, List[NLPOutput]]:
        """
        Loads documents from a benchmark JSON file and processes them.
        """
        corpus_path = Path(corpus_path)
        if not corpus_path.exists():
            raise FileNotFoundError(f"Corpus file not found: {corpus_path}")

        data = json.loads(corpus_path.read_text(encoding="utf-8"))
        documents = data.get("documents", [])
        return self.process_documents(documents, run_name=run_name or corpus_path.stem)

    def process_documents(
        self, documents: List[dict], run_name: str = "batch_run"
    ) -> tuple[BatchProcessingReport, List[NLPOutput]]:
        """
        Processes a list of document dictionaries or IDs.
        """
        start_time = time.time()
        run_id = f"{run_name}_{int(start_time)}"
        run_output_dir = self.output_base_dir / run_id
        run_output_dir.mkdir(parents=True, exist_ok=True)

        processed_outputs: List[NLPOutput] = []
        failures: List[dict] = []
        skipped = 0

        for doc_entry in documents:
            if isinstance(doc_entry, dict):
                if "document" in doc_entry and isinstance(doc_entry["document"], dict):
                    doc_id = doc_entry["document"].get("document_id")
                else:
                    doc_id = doc_entry.get("document_id")
            elif isinstance(doc_entry, (str, UUID)):
                doc_id = str(doc_entry)
            else:
                doc_id = None

            if not doc_id:
                skipped += 1
                continue

            try:
                output = self.pipeline.process_document(doc_id)
                processed_outputs.append(output)

                # Save individual output
                out_path = run_output_dir / f"{doc_id}.json"
                out_path.write_text(output.model_dump_json(indent=2), encoding="utf-8")

            except Exception as e:
                logger.error(f"Failed processing document {doc_id}: {e}")
                failures.append({
                    "document_id": str(doc_id),
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                })

        elapsed = time.time() - start_time

        report = BatchProcessingReport(
            total_documents=len(documents),
            processed_count=len(processed_outputs),
            failed_count=len(failures),
            skipped_count=skipped,
            elapsed_seconds=round(elapsed, 3),
            failures=failures,
            pipeline_version=self.pipeline.PIPELINE_VERSION,
            model_version="spacy-3.8.16+scispacy-0.6.2",
        )

        # Save summary report
        report_path = run_output_dir / "batch_report.json"
        report_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")

        return report, processed_outputs
