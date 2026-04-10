import { createContext, useContext, useState } from "react";

interface DataFreshnessCtx {
  isStale: boolean;
  markStale: () => void;
  markFresh: () => void;
}

const Ctx = createContext<DataFreshnessCtx>({
  isStale: false,
  markStale: () => {},
  markFresh: () => {},
});

export function DataFreshnessProvider({ children }: { children: React.ReactNode }) {
  const [isStale, setIsStale] = useState(false);
  return (
    <Ctx.Provider value={{ isStale, markStale: () => setIsStale(true), markFresh: () => setIsStale(false) }}>
      {children}
    </Ctx.Provider>
  );
}

export const useDataFreshness = () => useContext(Ctx);
