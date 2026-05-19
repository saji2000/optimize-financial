import { useEffect, useState } from "react";

import { getTranscripts } from "../api/transcripts";
import type { Transcript } from "../api/generated-types";

export function useTranscripts() {
  const [transcripts, setTranscripts] = useState<Transcript[]>([]);

  useEffect(() => {
    void getTranscripts().then(setTranscripts);
  }, []);

  return transcripts;
}

