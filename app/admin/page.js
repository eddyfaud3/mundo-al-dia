"use client";

import { useEffect, useState } from "react";

const empty={title:"",slug:"",excerpt:"",content:"",image_url:"",video_url:"",category:"Mundo",published:false};

export default function AdminPage(){
  const [articles,setArticles]=useState([]);
  const [form,setForm]=useState(empty);
  const [editing,setEditing]=useState(null);
  const [error,setError]=useState("");
  const [loading,setLoading]=useState(true);
  const [uploading,setUploading]=useState(false);
  const [uploadMessage,setUploadMessage]=useState("");
  const [facebook,setFacebook]=useState({configured:false,connected:false,pageName:""});
  const [facebookMessage,setFacebookMessage]=useState("");

  async function load(){
    setLoading(true);
    const r=await fetch("/api/admin/articles",{cache:"no-store"});
    if(r.status===401){location.href="/admin/login";return;}
    const d=await r.json();
    if(!r.ok){setError(d.error||"Error");setLoading(false);return;}
    setArticles(d);setLoading(false);
  }

  async function loadFacebook(){
    const r=await fetch("/api/facebook/status",{cache:"no-store"});
    if(r.status===401){location.href="/admin/login";return;}
    if(r.ok)setFacebook(await r.json());
  }

  useEffect(()=>{
    load();
    loadFacebook();
    const params=new URLSearchParams(location.search);
    const fb=params.get("facebook");
    const name=params.get("name");
    if(fb==="connected"){
      setFacebookMessage(`✅ Facebook conectado: ${name||"Mundo al Día"}`);
      loadFacebook();
      history.replaceState({}, "", "/admin");
    }else if(fb==="error"){
      setFacebookMessage("❌ No se pudo conectar Facebook. Revisa la configuración de Meta en Railway.");
      history.replaceState({}, "", "/admin");
    }
  },[]);

  function edit(a){setEditing(a.id);setForm({...a});window.scrollTo({top:0,behavior:"smooth"});}
  function change(e){const {name,value,type,checked}=e.target;setForm({...form,[name]:type==="checkbox"?checked:value});}

  async function uploadMedia(event){
    const file=event.target.files?.[0];
    event.target.value="";
    if(!file)return;

    setUploading(true);setUploadMessage("");setError("");
    try{
      const signResponse=await fetch("/api/upload",{method:"POST",headers:{Accept:"application/json"},cache:"no-store"});
      const signData=await signResponse.json();
      if(!signResponse.ok)throw new Error(signData.error||"No se pudo autorizar la carga.");

      const data=new FormData();
      data.append("file",file);
      data.append("api_key",signData.apiKey);
      data.append("timestamp",String(signData.timestamp));
      data.append("signature",signData.signature);
      data.append("folder",signData.folder||"mundo-al-dia");

      const uploadResponse=await fetch(`https://api.cloudinary.com/v1_1/${signData.cloudName}/auto/upload`,{method:"POST",body:data});
      const uploadData=await uploadResponse.json();
      if(!uploadResponse.ok)throw new Error(uploadData.error?.message||"La carga no se pudo completar.");

      if(uploadData.resource_type==="video"){
        setForm(prev=>({...prev,video_url:uploadData.secure_url}));
        setUploadMessage("✅ Video subido. La URL se agregó automáticamente.");
      }else{
        setForm(prev=>({...prev,image_url:uploadData.secure_url}));
        setUploadMessage("✅ Foto subida. La URL se agregó automáticamente.");
      }
    }catch(err){
      setError(err.message||"Ocurrió un error durante la carga.");
    }finally{
      setUploading(false);
    }
  }

  async function save(e){
    e.preventDefault();setError("");setUploadMessage("");setFacebookMessage("");
    if(!form.title.trim()||!form.slug.trim()){setError("Título y slug son obligatorios.");return;}
    const r=await fetch(editing?"/api/admin/articles/"+editing:"/api/admin/articles",{
      method:editing?"PUT":"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(form)
    });
    const d=await r.json();
    if(!r.ok){setError(d.error||"No se pudo guardar.");return;}
    if(d.facebook?.published){
      setFacebookMessage(`✅ Publicado automáticamente en Facebook: ${facebook.pageName||"Mundo al Día"}`);
    }else if(form.published && d.facebook?.reason){
      setFacebookMessage(`⚠️ La noticia se publicó en el sitio, pero Facebook no publicó: ${d.facebook.reason}`);
    }
    setForm(empty);setEditing(null);await load();
  }

  async function remove(id){
    if(!confirm("¿Eliminar esta noticia?"))return;
    const r=await fetch("/api/admin/articles/"+id,{method:"DELETE"});
    if(r.ok)load();else setError("No se pudo eliminar.");
  }

  async function logout(){await fetch("/api/admin/logout",{method:"POST"});location.href="/admin/login";}

  async function disconnectFacebook(){
    if(!confirm("¿Desconectar Facebook de Mundo al Día?"))return;
    const r=await fetch("/api/facebook/disconnect",{method:"POST"});
    if(r.ok){
      setFacebook({configured:true,connected:false,pageName:""});
      setFacebookMessage("Facebook desconectado.");
    }
  }

  return <main className="admin-page">
    <div className="admin-container">
    <header style={{display:"flex",justifyContent:"space-between",alignItems:"center",gap:16,flexWrap:"wrap"}}>
      <div><h1>🌎 Mundo al Día — Admin</h1><p>Gestiona tus noticias.</p></div>
      <div><a href="/" style={{marginRight:15}}>Ver sitio</a><button onClick={logout}>Cerrar sesión</button></div>
    </header>

    <section style={{border:"1px solid #ddd",borderRadius:12,padding:20,marginTop:20}}>
      <h2>📘 Publicación automática en Facebook</h2>
      {!facebook.configured ? (
        <p>⚠️ Falta configurar la aplicación de Meta en Railway.</p>
      ) : facebook.connected ? (
        <div>
          <p>✅ Conectado a la página <strong>{facebook.pageName}</strong>.</p>
          <p style={{fontSize:14}}>Cuando publiques una noticia nueva, Mundo al Día intentará publicarla automáticamente en Facebook.</p>
          <button type="button" onClick={disconnectFacebook}>Desconectar Facebook</button>
        </div>
      ) : (
        <div>
          <p>Conecta tu página de Facebook para activar la publicación automática.</p>
          <a className="button" href="/api/facebook/connect">🔗 Conectar Facebook</a>
        </div>
      )}
      {facebookMessage&&<p style={{marginTop:12}}>{facebookMessage}</p>}
    </section>

    <section style={{border:"1px solid #ddd",borderRadius:12,padding:20,marginTop:20}}>
      <h2>{editing?"Editar noticia":"Nueva noticia"}</h2>
      <form onSubmit={save} style={{display:"grid",gap:12}}>
        <input name="title" value={form.title} onChange={change} placeholder="Título" style={{padding:11}}/>
        <input name="slug" value={form.slug} onChange={change} placeholder="slug-ejemplo" style={{padding:11}}/>
        <input name="category" value={form.category} onChange={change} placeholder="Categoría" style={{padding:11}}/>
        <input name="excerpt" value={form.excerpt} onChange={change} placeholder="Resumen" style={{padding:11}}/>
        <textarea name="content" value={form.content} onChange={change} placeholder="Contenido de la noticia" rows={8} style={{padding:11}}/>

        <div style={{border:"1px solid #ddd",borderRadius:10,padding:15}}>
          <strong>📸🎥 Subir foto o video directamente</strong>
          <p style={{fontSize:14,margin:"8px 0"}}>Selecciona un archivo y se guardará en Cloudinary. La URL se colocará automáticamente en la noticia.</p>
          <input type="file" accept="image/*,video/*" onChange={uploadMedia} disabled={uploading}/>
          {uploading&&<p>⏳ Subiendo archivo...</p>}
          {uploadMessage&&<p>{uploadMessage}</p>}
        </div>

        <input name="image_url" value={form.image_url} onChange={change} placeholder="URL de la foto (se completa automáticamente)" style={{padding:11}}/>
        <input name="video_url" value={form.video_url} onChange={change} placeholder="URL del video (se completa automáticamente)" style={{padding:11}}/>
        <label><input type="checkbox" name="published" checked={!!form.published} onChange={change}/> Publicada</label>
        {error&&<p>❌ {error}</p>}
        <div><button type="submit" disabled={uploading} style={{padding:"11px 18px"}}>{editing?"Guardar cambios":"Crear noticia"}</button>{" "}<button type="button" onClick={()=>{setForm(empty);setEditing(null);setError("");setUploadMessage("")}}>Limpiar</button></div>
      </form>
    </section>

    <section style={{marginTop:30}}>
      <h2>Noticias</h2>
      {loading?<p>Cargando...</p>:articles.length===0?<p>No hay noticias todavía.</p>:articles.map(a=>
        <article key={a.id} style={{borderBottom:"1px solid #ddd",padding:"16px 0"}}>
          <strong>{a.title}</strong> — {a.category} — {a.published?"✅ Publicada":"⏸️ Borrador"} {a.facebook_post_id&&"— 📘 Facebook"}
          <div style={{marginTop:8}}><button onClick={()=>edit(a)}>Editar</button>{" "}<button onClick={()=>remove(a.id)}>Eliminar</button></div>
        </article>
      )}
    </section>
    </div>
  </main>
}
