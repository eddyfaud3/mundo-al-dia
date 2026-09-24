"use client";

import { useState } from "react";

export default function UploadPage() {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  function handleFileChange(event) {
    const selectedFile = event.target.files?.[0] || null;
    setFile(selectedFile);
    setResult(null);
    setError("");
  }

  async function handleUpload(event) {
    event.preventDefault();

    if (!file) {
      setError("Selecciona una foto o un video primero.");
      return;
    }

    setUploading(true);
    setError("");
    setResult(null);

    try {
      const signResponse = await fetch("/api/upload", {
        method: "POST",
        headers: {
          Accept: "application/json",
        },
        cache: "no-store",
      });

      const signText = await signResponse.text();

      let signData;

      try {
        signData = JSON.parse(signText);
      } catch {
        throw new Error("El servidor devolvió una respuesta no válida.");
      }

      if (!signResponse.ok) {
        throw new Error(
          signData.error || "No se pudo autorizar la carga."
        );
      }

      if (
        !signData.cloudName ||
        !signData.apiKey ||
        !signData.timestamp ||
        !signData.signature
      ) {
        throw new Error("Faltan datos para autorizar la carga.");
      }

      const formData = new FormData();

      formData.append("file", file);
      formData.append("api_key", signData.apiKey);
      formData.append("timestamp", String(signData.timestamp));
      formData.append("signature", signData.signature);
      formData.append(
        "folder",
        signData.folder || "mundo-al-dia"
      );

      const uploadResponse = await fetch(
        `https://api.cloudinary.com/v1_1/${signData.cloudName}/auto/upload`,
        {
          method: "POST",
          body: formData,
        }
      );

      const uploadText = await uploadResponse.text();

      let uploadData;

      try {
        uploadData = JSON.parse(uploadText);
      } catch {
        throw new Error(
          "Cloudinary devolvió una respuesta no válida."
        );
      }

      if (!uploadResponse.ok) {
        throw new Error(
          uploadData.error?.message ||
            "La carga no se pudo completar."
        );
      }

      setResult(uploadData);
    } catch (err) {
      console.error("Error de carga:", err);
      setError(
        err.message || "Ocurrió un error durante la carga."
      );
    } finally {
      setUploading(false);
    }
  }

  return (
    <main
      style={{
        maxWidth: "700px",
        margin: "0 auto",
        padding: "40px 20px",
        fontFamily: "Arial, sans-serif",
      }}
    >
      <h1>Subir foto / video</h1>

      <p>
        Selecciona una foto o un video para Mundo al Día.
      </p>

      <form onSubmit={handleUpload}>
        <input
          type="file"
          accept="image/*,video/*"
          onChange={handleFileChange}
        />

        {file && (
          <p style={{ marginTop: "15px" }}>
            Archivo seleccionado: <strong>{file.name}</strong>
          </p>
        )}

        <button
          type="submit"
          disabled={!file || uploading}
          style={{
            marginTop: "20px",
            padding: "12px 20px",
            cursor:
              !file || uploading ? "not-allowed" : "pointer",
            borderRadius: "8px",
            border: "none",
          }}
        >
          {uploading ? "Subiendo..." : "Subir"}
        </button>
      </form>

      {error && (
        <p style={{ marginTop: "20px" }}>
          ❌ {error}
        </p>
      )}

      {result && (
        <section style={{ marginTop: "30px" }}>
          <h2>✅ ¡Carga completada!</h2>

          <p>
            <strong>Tipo:</strong>{" "}
            {result.resource_type === "video"
              ? "Video"
              : "Foto"}
          </p>

          <p>
            <strong>URL:</strong>
          </p>

          <input
            value={result.secure_url || ""}
            readOnly
            style={{
              width: "100%",
              padding: "10px",
              boxSizing: "border-box",
            }}
          />
        </section>
      )}
    </main>
  );
}
