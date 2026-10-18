import { validApiPayload } from "./contracts";

export async function api<T>(path: string, body?: unknown): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      ...(body === undefined
        ? {}
        : {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          }),
    });
  } catch {
    throw new Error(
      "Veza sa lokalnim serverom nije dostupna. Proverite da je start-web.command pokrenut, pa pokušajte ponovo.",
    );
  }
  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error(
      "Server je vratio neispravan odgovor. Osvežite stranicu i pokušajte ponovo.",
    );
  }
  if (!response.ok)
    throw new Error(
      (data && typeof data.error === "string" && data.error) ||
        "Zahtev nije završen. Pokušajte ponovo.",
    );
  if (!validApiPayload(path, data))
    throw new Error(
      "Server je vratio neispravnu strukturu podataka. Pokušajte ponovo; postojeći razgovor ostaje dostupan.",
    );
  return data as T;
}

export function download(
  name: string,
  contents: string,
  type = "text/markdown",
) {
  const url = URL.createObjectURL(new Blob([contents], { type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
