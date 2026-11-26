import { createContext, useContext } from "react";

export const ContentReadOnlyContext = createContext(true);
export const useContentReadOnly = () => useContext(ContentReadOnlyContext);
export const readOnlyContentMessage = "Curated content is read-only in hosted mode.";
