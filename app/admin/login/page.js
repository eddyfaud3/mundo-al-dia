"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function AdminLogin() {
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const router = useRouter();

  async function submit(e) {
    e.preventDefault();
    setError("");
    const res = await fetch("/api/admin/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });
    const data = await res.json();
    if (!res.ok) {
      setError(data.error || "No se pudo iniciar sesión.");
      return;
    }
    router.push("/admin");
    router.refresh();
  }

  return (
    <main style={{maxWidth:420,margin:"80px auto",padding:24,fontFamily:"Arial,sans-serif"}}>
      <h1>🔐 Administración</h1>
      <p>Inicia sesión para administrar Mundo al Día.</p>
      <form onSubmit={submit}>
        <input
          type="password"
          value={password}
          onChange={e=>setPassword(e.target.value)}
          placeholder="Contraseña"
          autoComplete="current-password"
          style={{width:"100%",padding:12,boxSizing:"border-box"}}
        />
        <button type="submit" style={{marginTop:16,padding:"12px 20px"}}>Entrar</button>
      </form>
      {error && <p style={{marginTop:16}}>❌ {error}</p>}
    </main>
  );
}
