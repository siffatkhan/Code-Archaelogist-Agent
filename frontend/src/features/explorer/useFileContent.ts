import { useCallback, useEffect, useState } from "react";
import { USE_MOCK_DATA } from "@/lib/config";
import { filesService } from "@/services/files";
import { ApiError } from "@/types/api";
import type { RepositoryFileContent } from "@/types/file";
import { detectLanguage } from "./explorer.types";
import { MOCK_FILE_CONTENTS } from "./mocks/mockFiles";

export function useFileContent(repositoryId: string | undefined, path: string | null) {
  const [file, setFile] = useState<RepositoryFileContent | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!repositoryId || !path) {
      setFile(null);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      if (USE_MOCK_DATA) {
        await new Promise((resolve) => setTimeout(resolve, 250));
        const mock = MOCK_FILE_CONTENTS[path] ?? {
          path,
          content: `// No mock content available for ${path}.\n// Connect the backend to load real source.\n`,
          language: detectLanguage(path),
        };
        setFile(mock);
      } else {
        const data = await filesService.getFile(repositoryId, path);
        setFile({ ...data, language: data.language ?? detectLanguage(path) });
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load this file.");
    } finally {
      setIsLoading(false);
    }
  }, [repositoryId, path]);

  useEffect(() => {
    load();
  }, [load]);

  return { file, isLoading, error, refetch: load };
}
