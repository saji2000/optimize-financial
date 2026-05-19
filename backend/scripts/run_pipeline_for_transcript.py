import argparse
import json
from pathlib import Path

from app.pipeline.orchestrator import PipelineOrchestrator
from app.pipeline.transcript_loader import load_transcript


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the signal extraction pipeline locally.")
    parser.add_argument("transcript_path", type=Path)
    parser.add_argument("--transcript-id", default=None)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    raw_text = load_transcript(args.transcript_path)
    transcript_id = args.transcript_id or args.transcript_path.stem
    result = PipelineOrchestrator().run(transcript_id=transcript_id, raw_text=raw_text)
    output = json.dumps(result, indent=2)

    if args.output:
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    main()
