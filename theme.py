"""
Módulo de Estilo e Identidade Visual (Inspirado no Manual do ICMC/USP).
Aplica paleta de cores modernizada em tons metálicos (Aço Cobalto, Cobre Escovado, Titânio)
e injeta animação fluida de rede neural via Canvas (60fps) com nós ciano (#38bdf8) e âmbar (#f59e0b).
"""

import streamlit as st

# Paleta Metálica ICMC Modernizada
ICMC_COLORS = {
    # Azul Primário ICMC (Aço Cobalto / Titanium Blue)
    "steel_blue": "#38BDF8",
    "cobalt_dark": "#0F172A",
    "cobalt_surface": "#1E293B",
    
    # Laranja ICMC (Cobre Escovado / Cyber Amber)
    "copper_amber": "#F59E0B",
    "copper_glow": "#D97706",
    "copper_deep": "#B45309",
    
    # Tons Neutros Metálicos (Alumínio & Titânio)
    "titanium_bg": "#070B12",
    "titanium_card": "rgba(15, 23, 42, 0.75)",
    "metal_border": "rgba(148, 163, 184, 0.18)",
    "metal_border_highlight": "rgba(56, 189, 248, 0.4)",
    
    # Tipografia
    "text_primary": "#F8FAFC",
    "text_secondary": "#94A3B8",
    "text_muted": "#64748B",
    
    # Status
    "status_positive": "#10B981",
    "status_negative": "#EF4444",
}


def clean_html(html_str: str) -> str:
    """Remove quebras de linha e indentações que possam enganar o parser Markdown."""
    return " ".join(line.strip() for line in html_str.strip().splitlines() if line.strip())


def render_html(html_str: str):
    """Renderiza HTML de forma segura e limpa, garantindo que nunca seja exibido como texto puro."""
    st.markdown(clean_html(html_str), unsafe_allow_html=True)


def get_knot_svg_html(size: int = 28) -> str:
    """Retorna o SVG estilizado do nó topológico do ICMC em tom metálico."""
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" style="vertical-align: middle; flex-shrink: 0;">'
        '<defs>'
        '<linearGradient id="icmcGrad" x1="0%" y1="0%" x2="100%" y2="100%">'
        '<stop offset="0%" stop-color="#38BDF8"/>'
        '<stop offset="100%" stop-color="#1E3A8A"/>'
        '</linearGradient>'
        '<linearGradient id="amberGrad" x1="0%" y1="0%" x2="100%" y2="100%">'
        '<stop offset="0%" stop-color="#F59E0B"/>'
        '<stop offset="100%" stop-color="#D97706"/>'
        '</linearGradient>'
        '</defs>'
        '<path d="M50 15 C30 15, 15 30, 15 50 C15 70, 30 85, 50 85 C70 85, 85 70, 85 50" stroke="url(#icmcGrad)" stroke-width="8" stroke-linecap="round"/>'
        '<path d="M35 35 C45 25, 55 25, 65 35 C75 45, 75 55, 65 65 C55 75, 45 75, 35 65" stroke="url(#amberGrad)" stroke-width="6" stroke-linecap="round"/>'
        '</svg>'
    )


def inject_custom_theme():
    """
    Aplica o tema minimalista com acabamento metálico, backdrop-filter de desfoque
    e injeta animação fluida de rede neural via Canvas (60fps) com nós ciano e âmbar.
    """
    # 1. Estilização CSS com backdrop-filter blur(8px) nos cards e containers
    css = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

    /* Fundo da aplicação transparente para exibir o canvas fixo de rede neural */
    html, body, [data-testid="stAppViewContainer"], .stApp {{
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
        background-color: transparent !important;
        color: {ICMC_COLORS['text_primary']} !important;
    }}

    /* Cor base de fundo do container fixo do Streamlit */
    body {{
        background-color: {ICMC_COLORS['titanium_bg']} !important;
    }}

    [data-testid="stHeader"] {{
        background: transparent !important;
    }}

    /* Barra lateral com textura de titânio e blur */
    [data-testid="stSidebar"] {{
        background-color: rgba(11, 17, 30, 0.85) !important;
        backdrop-filter: blur(8px) !important;
        -webkit-backdrop-filter: blur(8px) !important;
        border-right: 1px solid {ICMC_COLORS['metal_border']} !important;
    }}

    /* Cartões Metálicos com backdrop-filter blur(8px) conforme solicitado */
    .metal-card {{
        background: rgba(15, 23, 42, 0.78) !important;
        backdrop-filter: blur(8px) !important;
        -webkit-backdrop-filter: blur(8px) !important;
        border: 1px solid {ICMC_COLORS['metal_border']} !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.06) !important;
        border-radius: 12px !important;
        padding: 18px 20px !important;
        transition: all 0.25s ease;
    }}

    .metal-card:hover {{
        border-color: rgba(56, 189, 248, 0.35) !important;
        box-shadow: 0 12px 36px 0 rgba(0, 0, 0, 0.55), inset 0 1px 0 rgba(255, 255, 255, 0.1) !important;
    }}

    /* Cabeçalho da Marca com blur */
    .brand-header {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 16px 22px;
        background: rgba(15, 23, 42, 0.78) !important;
        backdrop-filter: blur(8px) !important;
        -webkit-backdrop-filter: blur(8px) !important;
        border: 1px solid {ICMC_COLORS['metal_border']};
        border-radius: 12px;
        margin-bottom: 22px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.4);
    }}

    .brand-title {{
        font-size: 1.25rem;
        font-weight: 800;
        color: {ICMC_COLORS['text_primary']};
        letter-spacing: -0.02em;
        margin: 0;
    }}

    .brand-sub {{
        font-size: 0.82rem;
        color: {ICMC_COLORS['text_secondary']};
        margin-top: 3px;
    }}

    .brand-badge {{
        font-size: 0.68rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        padding: 3px 9px;
        border-radius: 4px;
        background: rgba(245, 158, 11, 0.15);
        color: {ICMC_COLORS['copper_amber']};
        border: 1px solid rgba(245, 158, 11, 0.35);
    }}

    /* Botões */
    div.stButton > button {{
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 600 !important;
        font-size: 0.82rem !important;
        letter-spacing: 0.05em !important;
        text-transform: uppercase !important;
        border-radius: 8px !important;
        padding: 10px 18px !important;
        border: 1px solid {ICMC_COLORS['metal_border']} !important;
        background: rgba(30, 41, 59, 0.85) !important;
        backdrop-filter: blur(8px) !important;
        color: {ICMC_COLORS['text_primary']} !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.08) !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }}

    div.stButton > button:hover {{
        border-color: {ICMC_COLORS['steel_blue']} !important;
        color: {ICMC_COLORS['steel_blue']} !important;
        box-shadow: 0 6px 18px rgba(56, 189, 248, 0.25) !important;
        transform: translateY(-1px);
    }}

    div.stButton > button[kind="primary"] {{
        background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%) !important;
        border: 1px solid rgba(245, 158, 11, 0.6) !important;
        color: #070B12 !important;
        font-weight: 700 !important;
        box-shadow: 0 4px 16px rgba(217, 119, 6, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.3) !important;
    }}

    div.stButton > button[kind="primary"]:hover {{
        background: linear-gradient(135deg, #FBBF24 0%, #F59E0B 100%) !important;
        color: #070B12 !important;
        box-shadow: 0 6px 22px rgba(245, 158, 11, 0.45) !important;
        transform: translateY(-1px);
    }}

    /* Abas */
    .stTabs [data-baseweb="tab-list"] {{
        background-color: rgba(15, 23, 42, 0.75);
        backdrop-filter: blur(8px);
        padding: 5px;
        border-radius: 10px;
        border: 1px solid {ICMC_COLORS['metal_border']};
        gap: 6px;
    }}

    .stTabs [data-baseweb="tab"] {{
        border-radius: 6px !important;
        font-weight: 600 !important;
        font-size: 0.82rem !important;
        color: {ICMC_COLORS['text_secondary']} !important;
        border: none !important;
        padding: 8px 16px !important;
    }}

    .stTabs [data-baseweb="tab"][aria-selected="true"] {{
        background: rgba(30, 41, 59, 0.9) !important;
        color: {ICMC_COLORS['text_primary']} !important;
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.12), 0 2px 8px rgba(0, 0, 0, 0.3) !important;
        border: 1px solid rgba(148, 163, 184, 0.25) !important;
    }}

    /* Métricas */
    div[data-testid="stMetricValue"] {{
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 1.85rem !important;
        font-weight: 700 !important;
        color: {ICMC_COLORS['text_primary']} !important;
    }}

    div[data-testid="stMetricLabel"] {{
        font-size: 0.72rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.06em !important;
        text-transform: uppercase !important;
        color: {ICMC_COLORS['text_secondary']} !important;
    }}

    /* Inputs e Formulários */
    input, select, textarea {{
        background-color: rgba(15, 23, 42, 0.8) !important;
        border: 1px solid {ICMC_COLORS['metal_border']} !important;
        color: {ICMC_COLORS['text_primary']} !important;
        border-radius: 6px !important;
    }}

    #MainMenu, footer {{visibility: hidden;}}
    header {{background: transparent !important;}}
    </style>
    """
    st.markdown(clean_html(css), unsafe_allow_html=True)

    # 2. Canvas fixo no fundo (position: fixed; inset: 0; z-index: -1; pointer-events: none;)
    # com animação fluida 60fps de rede neural e interação sutil com o mouse
    canvas_script = """
    <script>
    (function() {
        let canvas = document.getElementById("neural-bg-global");
        if (!canvas) {
            canvas = document.createElement("canvas");
            canvas.id = "neural-bg-global";
            canvas.style.cssText = "position: fixed; inset: 0; width: 100vw; height: 100vh; z-index: -1; pointer-events: none;";
            document.body.prepend(canvas);
        }
        if (window._neuralNetworkActive) return;
        window._neuralNetworkActive = true;

        const ctx = canvas.getContext("2d");

        let width = canvas.width = window.innerWidth;
        let height = canvas.height = window.innerHeight;

        window.addEventListener("resize", function() {
            width = canvas.width = window.innerWidth;
            height = canvas.height = window.innerHeight;
        });

        const mouse = { x: null, y: null, radius: 140 };

        window.addEventListener("mousemove", function(e) {
            mouse.x = e.clientX;
            mouse.y = e.clientY;
        });

        window.addEventListener("mouseleave", function() {
            mouse.x = null;
            mouse.y = null;
        });

        // Nós de rede neural
        const particleCount = Math.floor(Math.min(window.innerWidth, 1920) / 22);
        const particles = [];

        // Cores: ciano #38bdf8 e âmbar #f59e0b
        const colors = [
            { r: 56, g: 189, b: 248 },  // Ciano #38bdf8
            { r: 56, g: 189, b: 248 },  // Ciano #38bdf8
            { r: 245, g: 158, b: 11 }   // Âmbar #f59e0b
        ];

        for (let i = 0; i < particleCount; i++) {
            const col = colors[Math.floor(Math.random() * colors.length)];
            particles.push({
                x: Math.random() * width,
                y: Math.random() * height,
                vx: (Math.random() - 0.5) * 0.35,
                vy: (Math.random() - 0.5) * 0.35,
                radius: Math.random() * 1.5 + 2.0,
                color: col
            });
        }

        const maxDistance = 140;

        function animate() {
            ctx.clearRect(0, 0, width, height);

            for (let i = 0; i < particles.length; i++) {
                const p = particles[i];

                p.x += p.vx;
                p.y += p.vy;

                if (p.x < -10) p.x = width + 10;
                if (p.x > width + 10) p.x = -10;
                if (p.y < -10) p.y = height + 10;
                if (p.y > height + 10) p.y = -10;

                if (mouse.x !== null && mouse.y !== null) {
                    const dx = mouse.x - p.x;
                    const dy = mouse.y - p.y;
                    const dist = Math.sqrt(dx * dx + dy * dy);
                    if (dist < mouse.radius && dist > 0) {
                        const force = (1 - dist / mouse.radius) * 1.2;
                        p.x -= (dx / dist) * force;
                        p.y -= (dy / dist) * force;
                    }
                }

                ctx.beginPath();
                ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
                ctx.fillStyle = "rgba(" + p.color.r + ", " + p.color.g + ", " + p.color.b + ", 0.4)";
                ctx.fill();

                for (let j = i + 1; j < particles.length; j++) {
                    const p2 = particles[j];
                    const dx = p.x - p2.x;
                    const dy = p.y - p2.y;
                    const dist = Math.sqrt(dx * dx + dy * dy);

                    if (dist < maxDistance) {
                        const alpha = (1 - dist / maxDistance) * 0.22;
                        if (alpha >= 0.03) {
                            ctx.beginPath();
                            ctx.moveTo(p.x, p.y);
                            ctx.lineTo(p2.x, p2.y);
                            ctx.strokeStyle = "rgba(" + p.color.r + ", " + p.color.g + ", " + p.color.b + ", " + alpha.toFixed(3) + ")";
                            ctx.lineWidth = 0.9;
                            ctx.stroke();
                        }
                    }
                }
            }

            requestAnimationFrame(animate);
        }

        animate();
    })();
    </script>
    """
    st.html(canvas_script, unsafe_allow_javascript=True)

    # 3. Relógio em tempo real contínuo (24/7, atualizado a cada 250ms via DOM)
    clock_script = """
    <script>
    (function() {
        function tickLiveClock() {
            const now = new Date();
            const h = String(now.getHours()).padStart(2, '0');
            const m = String(now.getMinutes()).padStart(2, '0');
            const s = String(now.getSeconds()).padStart(2, '0');
            const timeStr = `${h}:${m}:${s}`;

            const clockDisplays = document.querySelectorAll('.live-clock-display');
            for (let i = 0; i < clockDisplays.length; i++) {
                clockDisplays[i].textContent = timeStr;
            }

            const dateDisplays = document.querySelectorAll('.live-clock-date');
            if (dateDisplays.length > 0) {
                const dateStr = now.toLocaleDateString('pt-BR', { weekday: 'short', day: '2-digit', month: '2-digit', year: 'numeric' });
                for (let i = 0; i < dateDisplays.length; i++) {
                    dateDisplays[i].textContent = dateStr;
                }
            }
        }

        tickLiveClock();
        if (window._liveClockInterval) {
            clearInterval(window._liveClockInterval);
        }
        window._liveClockInterval = setInterval(tickLiveClock, 250);
    })();
    </script>
    """
    st.html(clock_script, unsafe_allow_javascript=True)

