import { useEffect, useState } from "react";

import { getSignals } from "../api/signals";
import type { Signal } from "../api/generated-types";

export function useSignals() {
  const [signals, setSignals] = useState<Signal[]>([]);

  useEffect(() => {
    void getSignals().then(setSignals);
  }, []);

  return signals;
}

