import { useEffect, useState } from "react";

import { getPipelineRuns } from "../api/pipelineRuns";
import type { PipelineRun } from "../api/generated-types";

export function usePipelineRuns() {
  const [pipelineRuns, setPipelineRuns] = useState<PipelineRun[]>([]);

  useEffect(() => {
    void getPipelineRuns().then(setPipelineRuns);
  }, []);

  return pipelineRuns;
}

