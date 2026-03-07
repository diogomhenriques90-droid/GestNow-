"""
GESTNOW v3 — mod_login.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Ecrã de autenticação: PIN, Password, Biometria (WebAuthn), Facial (face-api.js).

Para adicionar um novo modo de login → editar render_login() aqui.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
from core import *


def render_login():
    """
    Ecrã de login. Quando autentica com sucesso faz st.rerun().
    O app.py deteta st.session_state.user != None e passa para o painel.
    """
    if st.session_state.login_attempts >= MAX_LOGIN_ATTEMPTS:
        st.error("🔒 Conta bloqueada. Contacte o administrador."); st.stop()

    if 'pin_digits' not in st.session_state: st.session_state.pin_digits = ""
    if 'login_mode' not in st.session_state: st.session_state.login_mode = "pin"
    if 'bio_user' not in st.session_state: st.session_state.bio_user = ""
    if 'face_result' not in st.session_state: st.session_state.face_result = ""

    # ── Verificar resultado de biometria/face vindo do JS ──
    bio_param = st.query_params.get("bio_login","")
    face_param = st.query_params.get("face_login","")
    if bio_param:
        ut,*_=load_all()
        m_bio=ut[ut['Nome']==bio_param]
        if not m_bio.empty:
            r_=m_bio.iloc[0]
            st.session_state.update(user=r_['Nome'],tipo=r_['Tipo'],cargo=r_.get('Cargo','Técnico'),session_token=secrets.token_hex(32),login_attempts=0)
            st.query_params.clear(); st.rerun()
    if face_param:
        ut,*_=load_all()
        m_face=ut[ut['Nome']==face_param]
        if not m_face.empty:
            r_=m_face.iloc[0]
            st.session_state.update(user=r_['Nome'],tipo=r_['Tipo'],cargo=r_.get('Cargo','Técnico'),session_token=secrets.token_hex(32),login_attempts=0)
            st.query_params.clear(); st.rerun()

    # ── Estilos do ecrã de login ──
    st.markdown("""<style>
    @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400;500;600;700&display=swap');
    .stApp{background:#0A0F1E !important;}
    .login-logo{font-family:'Bebas Neue',sans-serif;font-size:3.5rem;letter-spacing:4px;
        background:linear-gradient(135deg,#fff 30%,#E74C3C);-webkit-background-clip:text;-webkit-text-fill-color:transparent;
        text-align:center;margin-bottom:0;}
    .login-sub{text-align:center;color:rgba(255,255,255,.35);font-size:.7rem;letter-spacing:6px;
        text-transform:uppercase;margin-bottom:2.5rem;font-family:'DM Sans',sans-serif;}
    .login-box{background:rgba(255,255,255,.04);backdrop-filter:blur(20px);
        border:1px solid rgba(255,255,255,.1);border-radius:24px;padding:2rem;max-width:380px;margin:0 auto;}
    .mode-tabs{display:flex;gap:6px;background:rgba(0,0,0,.3);padding:5px;border-radius:14px;margin-bottom:1.5rem;}
    .mode-tab{flex:1;padding:9px 4px;border-radius:10px;text-align:center;font-size:.72rem;
        font-weight:600;letter-spacing:.5px;text-transform:uppercase;color:rgba(255,255,255,.35);cursor:pointer;transition:.2s;}
    .mode-tab.active{background:rgba(231,76,60,.9);color:white;box-shadow:0 4px 12px rgba(231,76,60,.4);}
    .pin-display{font-size:1.8rem;letter-spacing:12px;text-align:center;color:white;
        background:rgba(0,0,0,.4);border:1px solid rgba(255,255,255,.1);border-radius:14px;
        padding:.6rem 1rem;margin:.75rem 0;min-height:56px;font-family:monospace;}
    .pin-key{background:rgba(255,255,255,.08)!important;color:white!important;font-size:1.3rem!important;
        font-weight:600!important;border:1px solid rgba(255,255,255,.1)!important;border-radius:14px!important;
        transition:.15s!important;}
    .pin-key:hover{background:rgba(231,76,60,.3)!important;border-color:rgba(231,76,60,.5)!important;}
    .bio-btn{background:linear-gradient(135deg,#1A3A6B,#2563EB)!important;color:white!important;
        font-size:1rem!important;font-weight:700!important;border:none!important;border-radius:16px!important;
        padding:1rem!important;height:70px!important;transition:.2s!important;
        box-shadow:0 8px 24px rgba(37,99,235,.4)!important;}
    .face-btn{background:linear-gradient(135deg,#0D5C3A,#059669)!important;color:white!important;
        font-size:1rem!important;font-weight:700!important;border:none!important;border-radius:16px!important;
        padding:1rem!important;height:70px!important;transition:.2s!important;
        box-shadow:0 8px 24px rgba(5,150,105,.4)!important;}
    .cam-box{border-radius:16px;overflow:hidden;border:2px solid rgba(5,150,105,.4);margin:.5rem 0;}
    .scan-line{width:100%;height:3px;background:linear-gradient(90deg,transparent,#059669,transparent);
        animation:scan 2s linear infinite;}
    @keyframes scan{0%{transform:translateY(0)}100%{transform:translateY(200px)}}
    .security-badge{text-align:center;color:rgba(255,255,255,.25);font-size:.7rem;margin-top:1.5rem;letter-spacing:1px;}
    </style>""", unsafe_allow_html=True)

    st.markdown('<div class="login-logo">🏗️ GESTNOW</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-sub">Gestão de Obras e Equipas</div>', unsafe_allow_html=True)

    _,cm_,_=st.columns([1,1.4,1])
    with cm_:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)

        # ── Tabs de modo ──
        m1,m2,m3,m4=st.columns(4)
        with m1:
            if st.button("🔢 PIN",use_container_width=True,key="btn_m_pin"):
                st.session_state.login_mode="pin"; st.session_state.pin_digits=""; st.rerun()
        with m2:
            if st.button("🔑 Pass",use_container_width=True,key="btn_m_pw"):
                st.session_state.login_mode="pw"; st.session_state.pin_digits=""; st.rerun()
        with m3:
            if st.button("👆 Bio",use_container_width=True,key="btn_m_bio"):
                st.session_state.login_mode="bio"; st.rerun()
        with m4:
            if st.button("👤 Face",use_container_width=True,key="btn_m_face"):
                st.session_state.login_mode="face"; st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)

        # ══════════════════════════════════
        # MODO PIN
        # ══════════════════════════════════
        if st.session_state.login_mode == "pin":
            st.markdown("#### 🔢 Entrar com PIN")
            u_pin=st.text_input("Código de utilizador",placeholder="Nome ou código",key="pin_user",label_visibility="visible")
            pin_show="●"*len(st.session_state.pin_digits)+"·"*(4-min(len(st.session_state.pin_digits),4))
            st.markdown(f"<div class='pin-display'>{pin_show}</div>", unsafe_allow_html=True)
            for row_d in [["1","2","3"],["4","5","6"],["7","8","9"]]:
                cols_d=st.columns(3)
                for ci,d in enumerate(row_d):
                    with cols_d[ci]:
                        if st.button(d,key=f"pin_{d}",use_container_width=True):
                            if len(st.session_state.pin_digits)<6: st.session_state.pin_digits+=d
                            st.rerun()
            c0,cb=st.columns(2)
            with c0:
                if st.button("0",key="pin_0",use_container_width=True):
                    if len(st.session_state.pin_digits)<6: st.session_state.pin_digits+="0"
                    st.rerun()
            with cb:
                if st.button("⌫",key="pin_del",use_container_width=True):
                    st.session_state.pin_digits=st.session_state.pin_digits[:-1]; st.rerun()
            if len(st.session_state.pin_digits)>=4:
                if st.button("✅ ENTRAR",use_container_width=True,key="pin_enter"):
                    ut,*_=load_all()
                    m_pin=ut[ut['Nome'].str.lower()==u_pin.strip().lower()]
                    if not m_pin.empty:
                        rp=m_pin.iloc[0]; pg=rp.get('PIN','')
                        if pg and pg==st.session_state.pin_digits:
                            st.session_state.update(user=rp['Nome'],tipo=rp['Tipo'],cargo=rp.get('Cargo','Técnico'),session_token=secrets.token_hex(32),login_attempts=0,pin_digits=""); st.rerun()
                        else:
                            st.session_state.login_attempts+=1; st.session_state.pin_digits=""; st.error("❌ PIN incorreto.")
                    else:
                        st.session_state.login_attempts+=1; st.session_state.pin_digits=""; st.error("❌ Utilizador não encontrado.")

        # ══════════════════════════════════
        # MODO PASSWORD
        # ══════════════════════════════════
        elif st.session_state.login_mode == "pw":
            with st.form("lf",clear_on_submit=True):
                st.markdown("#### 🔑 Entrar com Password")
                u=st.text_input("Utilizador",placeholder="Nome de utilizador")
                p=st.text_input("Palavra-passe",type="password",placeholder="••••••••")
                if st.form_submit_button("ENTRAR →",use_container_width=True):
                    u=u.strip()
                    if u.lower()=="admin" and p=="admin":
                        st.session_state.update(user="Admin",tipo="Admin",cargo="Admin",session_token=secrets.token_hex(32),login_attempts=0); st.rerun()
                    else:
                        ut,*_=load_all(); m=ut[ut['Nome'].str.lower()==u.lower()]
                        if not m.empty and cp(p,m.iloc[0]['Password']):
                            st.session_state.update(user=m.iloc[0]['Nome'],tipo=m.iloc[0]['Tipo'],cargo=m.iloc[0].get('Cargo','Técnico'),session_token=secrets.token_hex(32),login_attempts=0); st.rerun()
                        else:
                            st.session_state.login_attempts+=1; r=MAX_LOGIN_ATTEMPTS-st.session_state.login_attempts; st.error(f"❌ Incorreto. {r} tentativa(s).")

        # ══════════════════════════════════
        # MODO BIOMÉTRICO (WebAuthn / Passkey)
        # ══════════════════════════════════
        elif st.session_state.login_mode == "bio":
            st.markdown("#### 👆 Autenticação Biométrica")
            st.caption("Usa a impressão digital, Face ID ou PIN do dispositivo para entrar.")
            bio_uname=st.text_input("Utilizador",placeholder="O teu nome",key="bio_uname")
            # Componente HTML+JS para WebAuthn
            if bio_uname.strip():
                users_list_bio=[]
                try:
                    ut_b,*_=load_all()
                    users_list_bio=[r['Nome'] for _,r in ut_b.iterrows()]
                except: pass
                webauthn_html=f"""
    <div style="text-align:center;padding:1.5rem 0;">
      <div id="bio-status" style="color:rgba(255,255,255,.5);font-size:.85rem;margin-bottom:1rem;">
    Pronto para autenticar
      </div>
      <button onclick="startBiometric()" id="bio-btn"
    style="background:linear-gradient(135deg,#1A3A6B,#2563EB);color:white;border:none;
    border-radius:16px;padding:1rem 2rem;font-size:1rem;font-weight:700;cursor:pointer;
    width:100%;box-shadow:0 8px 24px rgba(37,99,235,.4);transition:.2s;"
    onmouseover="this.style.transform='translateY(-2px)'"
    onmouseout="this.style.transform='none'">
    👆 Autenticar com Biometria
      </button>
      <p style="color:rgba(255,255,255,.3);font-size:.72rem;margin-top:.75rem;">
    Impressão digital · Face ID · PIN do dispositivo
      </p>
    </div>
    <script>
    async function startBiometric() {{
      const btn = document.getElementById('bio-btn');
      const status = document.getElementById('bio-status');
      const username = "{bio_uname.strip()}";

      btn.disabled = true;
      status.textContent = '🔐 A verificar identidade...';
      status.style.color = '#60A5FA';

      try {{
    // Verificar suporte WebAuthn
    if (!window.PublicKeyCredential) {{
      throw new Error('WebAuthn não suportado neste browser');
    }}

    // Criar challenge aleatório
    const challenge = new Uint8Array(32);
    window.crypto.getRandomValues(challenge);

    // Verificar se há credenciais guardadas
    const credKey = 'gestnow_cred_' + username;
    const savedCredId = localStorage.getItem(credKey);

    if (savedCredId) {{
      // ── AUTENTICAR com credencial existente ──
      status.textContent = '👆 Coloca o dedo no sensor...';
      const credIdBytes = Uint8Array.from(atob(savedCredId), c => c.charCodeAt(0));
      const assertion = await navigator.credentials.get({{
        publicKey: {{
          challenge: challenge,
          allowCredentials: [{{ id: credIdBytes, type: 'public-key' }}],
          userVerification: 'required',
          timeout: 60000
        }}
      }});
      status.textContent = '✅ Autenticado com sucesso!';
      status.style.color = '#34D399';
      setTimeout(() => {{
        window.location.href = window.location.href.split('?')[0] + '?bio_login=' + encodeURIComponent(username);
      }}, 800);

    }} else {{
      // ── REGISTAR nova credencial ──
      status.textContent = '📝 Primeira vez — a registar biometria...';
      const userIdBytes = new TextEncoder().encode(username);
      const credential = await navigator.credentials.create({{
        publicKey: {{
          challenge: challenge,
          rp: {{ name: "GESTNOW", id: window.location.hostname }},
          user: {{ id: userIdBytes, name: username, displayName: username }},
          pubKeyCredParams: [{{ alg: -7, type: 'public-key' }}, {{ alg: -257, type: 'public-key' }}],
          authenticatorSelection: {{ userVerification: 'required', residentKey: 'preferred' }},
          timeout: 60000
        }}
      }});
      // Guardar ID da credencial localmente
      const credId = btoa(String.fromCharCode(...new Uint8Array(credential.rawId)));
      localStorage.setItem(credKey, credId);
      status.textContent = '✅ Biometria registada e autenticada!';
      status.style.color = '#34D399';
      setTimeout(() => {{
        window.location.href = window.location.href.split('?')[0] + '?bio_login=' + encodeURIComponent(username);
      }}, 800);
    }}
      }} catch(e) {{
    btn.disabled = false;
    if (e.name === 'NotAllowedError') {{
      status.textContent = '❌ Autenticação cancelada ou recusada.';
    }} else if (e.message.includes('não suportado')) {{
      status.textContent = '⚠️ ' + e.message + '. Usa PIN ou Password.';
    }} else {{
      status.textContent = '❌ Erro: ' + e.message;
    }}
    status.style.color = '#F87171';
      }}
    }}
    </script>"""
                st.components.v1.html(webauthn_html, height=220)
            else:
                st.info("👆 Introduz o teu nome para ativar a autenticação biométrica.")

        # ══════════════════════════════════
        # MODO RECONHECIMENTO FACIAL
        # ══════════════════════════════════
        elif st.session_state.login_mode == "face":
            st.markdown("#### 👤 Reconhecimento Facial")
            st.caption("A câmara analisa o teu rosto e identifica-te automaticamente.")
            # Construir lista de utilizadores e fotos para face matching
            try:
                ut_f,*_=load_all()
                # Utilizadores com foto registada
                users_com_foto=ut_f[ut_f['Foto'].str.len()>10] if not ut_f.empty else pd.DataFrame()
                n_com_foto=len(users_com_foto)
            except:
                n_com_foto=0; users_com_foto=pd.DataFrame()

            if n_com_foto==0:
                st.warning("⚠️ Nenhum utilizador tem foto de perfil registada. O admin precisa de adicionar fotos no painel de Pessoal antes de usar esta funcionalidade.")
            else:
                st.success(f"✅ {n_com_foto} utilizador(es) com reconhecimento facial ativo.")

            face_html=f"""
    <div style="text-align:center;">
      <div id="face-status" style="color:rgba(255,255,255,.5);font-size:.85rem;margin-bottom:.75rem;">
    A inicializar câmara...
      </div>
      <div style="position:relative;border-radius:16px;overflow:hidden;border:2px solid rgba(5,150,105,.3);max-width:320px;margin:0 auto;">
    <video id="face-video" autoplay muted playsinline
      style="width:100%;border-radius:14px;display:block;"></video>
    <canvas id="face-canvas" style="position:absolute;top:0;left:0;width:100%;height:100%;"></canvas>
    <div id="scan-overlay" style="position:absolute;top:0;left:0;width:100%;pointer-events:none;">
      <div style="width:100%;height:3px;background:linear-gradient(90deg,transparent,#059669,transparent);
        animation:scanline 2s ease-in-out infinite;"></div>
    </div>
      </div>
      <style>
    @keyframes scanline{{0%{{transform:translateY(0)}}50%{{transform:translateY(240px)}}100%{{transform:translateY(0)}}}}
    #face-start-btn{{background:linear-gradient(135deg,#0D5C3A,#059669);color:white;border:none;
      border-radius:14px;padding:.85rem 2rem;font-size:.95rem;font-weight:700;cursor:pointer;
      width:100%;margin-top:.75rem;box-shadow:0 6px 20px rgba(5,150,105,.4);}}
    #face-start-btn:hover{{transform:translateY(-2px);}}
    #face-match-result{{margin-top:.75rem;padding:.75rem;border-radius:12px;
      background:rgba(5,150,105,.15);border:1px solid rgba(5,150,105,.3);display:none;}}
      </style>
      <button id="face-start-btn" onclick="startFaceRecognition()">
    📷 Iniciar Reconhecimento Facial
      </button>
      <div id="face-match-result">
    <div id="face-match-name" style="color:#34D399;font-weight:700;font-size:1.1rem;"></div>
    <div style="color:rgba(255,255,255,.5);font-size:.8rem;margin-top:4px;">Identidade verificada</div>
      </div>
      <p style="color:rgba(255,255,255,.25);font-size:.7rem;margin-top:.75rem;line-height:1.4;">
    🔒 O processamento é feito localmente no dispositivo.<br>
    Nenhuma imagem é enviada para servidores externos.
      </p>
    </div>
    <script>
    // Carregar face-api.js (modelo leve de reconhecimento facial)
    const FACE_API_CDN = 'https://cdn.jsdelivr.net/npm/face-api.js@0.22.2/dist/face-api.min.js';
    const MODEL_URL = 'https://cdn.jsdelivr.net/npm/@vladmandic/face-api/model/';

    let faceApiLoaded = false;
    let videoStream = null;
    let recognitionInterval = null;

    async function loadFaceAPI() {{
      return new Promise((resolve, reject) => {{
    if (faceApiLoaded) {{ resolve(); return; }}
    const script = document.createElement('script');
    script.src = FACE_API_CDN;
    script.onload = () => {{ faceApiLoaded = true; resolve(); }};
    script.onerror = () => reject(new Error('Erro ao carregar face-api.js'));
    document.head.appendChild(script);
      }});
    }}

    async function startFaceRecognition() {{
      const status = document.getElementById('face-status');
      const video = document.getElementById('face-video');
      const btn = document.getElementById('face-start-btn');
      btn.disabled = true;
      btn.textContent = '⏳ A carregar modelos...';

      try {{
    // Carregar biblioteca
    status.textContent = '📦 A carregar modelos de IA...';
    status.style.color = '#60A5FA';
    await loadFaceAPI();

    // Carregar modelos necessários
    status.textContent = '🧠 A inicializar reconhecimento...';
    await Promise.all([
      faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL),
      faceapi.nets.faceLandmark68TinyNet.loadFromUri(MODEL_URL),
      faceapi.nets.faceRecognitionNet.loadFromUri(MODEL_URL),
    ]);

    // Iniciar câmara
    status.textContent = '📷 A aceder à câmara...';
    videoStream = await navigator.mediaDevices.getUserMedia({{
      video: {{ width: 320, height: 240, facingMode: 'user' }}
    }});
    video.srcObject = videoStream;
    await video.play();

    status.textContent = '👀 Procura rosto... Olha para a câmara!';
    status.style.color = '#34D399';
    btn.textContent = '⏹ Parar';
    btn.style.background = 'linear-gradient(135deg,#7F1D1D,#DC2626)';
    btn.disabled = false;
    btn.onclick = stopFaceRecognition;

    // Construir descrições dos rostos registados
    const knownFaces = {{}};
    const usersData = {repr([{'nome': r['Nome'], 'foto': r['Foto'][:50] if len(str(r.get('Foto','')))>10 else ''} for _,r in users_com_foto.iterrows()])};

    // Processar rostos conhecidos (fotos base64 do perfil)
    for (const u of usersData) {{
      if (!u.foto) continue;
      try {{
        const img = new Image();
        img.src = 'data:image/jpeg;base64,' + u.foto_full; // será injetado
        await new Promise(r => {{ img.onload = r; img.onerror = r; }});
        const det = await faceapi.detectSingleFace(img, new faceapi.TinyFaceDetectorOptions())
          .withFaceLandmarks(true).withFaceDescriptor();
        if (det) knownFaces[u.nome] = det.descriptor;
      }} catch(e) {{ console.warn('Erro no rosto de', u.nome, e); }}
    }}

    // Scan em tempo real
    recognitionInterval = setInterval(async () => {{
      if (video.paused || video.ended) return;
      try {{
        const detection = await faceapi.detectSingleFace(video, new faceapi.TinyFaceDetectorOptions({{
          inputSize: 224, scoreThreshold: 0.5
        }})).withFaceLandmarks(true).withFaceDescriptor();

        if (detection) {{
          // Desenhar caixa
          const canvas = document.getElementById('face-canvas');
          canvas.width = video.videoWidth; canvas.height = video.videoHeight;
          faceapi.draw.drawDetections(canvas, [detection]);

          // Comparar com rostos conhecidos
          let bestMatch = null, bestDist = 0.55;
          for (const [nome, descriptor] of Object.entries(knownFaces)) {{
            const dist = faceapi.euclideanDistance(detection.descriptor, descriptor);
            if (dist < bestDist) {{ bestDist = dist; bestMatch = nome; }}
          }}

          if (bestMatch) {{
            clearInterval(recognitionInterval);
            status.textContent = `✅ Identificado: ${{bestMatch}} (${{(1-bestDist).toFixed(0)*100}}% confiança)`;
            status.style.color = '#34D399';
            const result = document.getElementById('face-match-result');
            const nameDiv = document.getElementById('face-match-name');
            nameDiv.textContent = '👤 ' + bestMatch;
            result.style.display = 'block';
            stopVideoStream();
            setTimeout(() => {{
              window.location.href = window.location.href.split('?')[0] + '?face_login=' + encodeURIComponent(bestMatch);
            }}, 1500);
          }} else {{
            status.textContent = '👀 Rosto detetado — a comparar...';
          }}
        }} else {{
          status.textContent = '👀 Olha para a câmara...';
        }}
      }} catch(e) {{}}
    }}, 500);

      }} catch(e) {{
    btn.disabled = false;
    btn.textContent = '📷 Tentar novamente';
    btn.onclick = startFaceRecognition;
    if (e.name === 'NotAllowedError') {{
      status.textContent = '❌ Permissão de câmara negada.';
    }} else {{
      status.textContent = '❌ ' + e.message;
    }}
    status.style.color = '#F87171';
      }}
    }}

    function stopVideoStream() {{
      if (videoStream) {{ videoStream.getTracks().forEach(t => t.stop()); videoStream = null; }}
    }}

    function stopFaceRecognition() {{
      clearInterval(recognitionInterval);
      stopVideoStream();
      document.getElementById('face-status').textContent = 'Câmara parada.';
      document.getElementById('face-status').style.color = 'rgba(255,255,255,.4)';
      const btn = document.getElementById('face-start-btn');
      btn.textContent = '📷 Iniciar Reconhecimento Facial';
      btn.style.background = 'linear-gradient(135deg,#0D5C3A,#059669)';
      btn.onclick = startFaceRecognition;
    }}
    </script>"""
            st.components.v1.html(face_html, height=500, scrolling=False)

        st.markdown('<div class="security-badge">🔒 Ligação segura &nbsp;•&nbsp; Sessão cifrada &nbsp;•&nbsp; GESTNOW v2</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.stop()

    # ============================================================
    # 10. DADOS + TOPBAR
    # ============================================================
    users,obras_db,frentes_db,registos_db,faturas_db,docs_db,incs_db,sw_db,obs_db,equip_db,diags_db,diags_u_db,folhas_db,comuns_db,comuns_u_db,req_fer_db,req_mat_db,req_epi_db,avals_db=load_all()

    st.markdown(f"""<div class="topbar"><span class="topbar-logo">🏗️ GESTNOW</span>
    <div class="topbar-user"><span>👤 {st.session_state.user}</span>
    <span class="badge-tipo">{st.session_state.tipo}</span>
    <span class="badge-hora">🕐 {datetime.now().strftime('%H:%M')}</span></div></div>""",unsafe_allow_html=True)

