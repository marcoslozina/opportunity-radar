from __future__ import annotations

import httpx
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

API_BASE = "http://localhost:8000"

PALETTE = {
    "primary": "#3B82F6",
    "success": "#22C55E",
    "warning": "#F97316",
    "danger": "#EF4444",
    "purple": "#A855F7",
    "muted": "#6B7280",
    "surface": "#1E293B",
    "surface2": "#263348",
    "bg": "#0F172A",
    "border": "#334155",
    "text_muted": "#94A3B8",
    "text_faint": "#64748B",
}

DISCOVERY_MODE_COLORS = {
    "content": PALETTE["primary"],
    "product": PALETTE["success"],
    "both": PALETTE["purple"],
}

DISCOVERY_MODE_LABELS = {
    "content": "📝 Content — genera ideas de contenido editorial",
    "product": "📦 Product — detecta oportunidades de producto digital",
    "both": "✨ Both — analiza contenido y producto al mismo tiempo",
}

PRODUCT_TYPE_COLORS = {
    "ebook": PALETTE["primary"],
    "micro-saas": PALETTE["success"],
    "service": PALETTE["warning"],
    "digital-product": PALETTE["purple"],
}

CONFIDENCE_COLORS = {
    "high": PALETTE["success"],
    "medium": PALETTE["warning"],
    "low": PALETTE["danger"],
}

st.set_page_config(
    layout="wide",
    page_title="Opportunity Radar",
    page_icon="📡",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------

st.markdown(
    """
    <style>
    /* ---------- base ---------- */
    .stApp { background: #0F172A; }

    /* ---------- sidebar ---------- */
    [data-testid="stSidebar"] {
        background: #0D1B2A !important;
        border-right: 1px solid #1E293B;
    }
    [data-testid="stSidebar"] .block-container { padding: 1.2rem 1rem; }

    /* ---------- section header ---------- */
    .section-header {
        margin-bottom: 0.25rem;
    }
    .section-header h2 {
        font-size: 1.6rem;
        font-weight: 700;
        margin: 0;
    }
    .section-subtitle {
        color: #64748B;
        font-size: 0.9rem;
        margin-bottom: 1.5rem;
    }

    /* ---------- cards ---------- */
    .card {
        background: #1E293B;
        border: 1px solid #263348;
        border-radius: 14px;
        padding: 18px 20px;
    }
    .card-hover:hover {
        border-color: #3B82F6;
        transition: border-color 0.2s;
    }

    /* ---------- badges ---------- */
    .badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 9999px;
        font-size: 0.72rem;
        font-weight: 600;
        color: #fff;
        letter-spacing: 0.02em;
    }
    .badge-manual {
        background: #334155;
        border: 1px dashed #64748B;
    }

    /* ---------- score bar ---------- */
    .score-bar-wrap {
        background: #334155;
        border-radius: 9999px;
        height: 6px;
        width: 100%;
        margin-top: 5px;
    }
    .score-bar-fill {
        height: 6px;
        border-radius: 9999px;
    }

    /* ---------- product card ---------- */
    .product-card {
        background: #1E293B;
        border: 1px solid #263348;
        border-radius: 14px;
        padding: 18px;
        height: 100%;
    }
    .price-range {
        font-size: 1.25rem;
        font-weight: 700;
        color: #22C55E;
        margin: 4px 0 0;
    }

    /* ---------- niche row ---------- */
    .niche-row {
        background: #1E293B;
        border: 1px solid #263348;
        border-radius: 10px;
        padding: 12px 16px;
        margin-bottom: 10px;
    }

    /* ---------- empty state ---------- */
    .empty-state {
        text-align: center;
        padding: 60px 20px;
        color: #64748B;
    }
    .empty-state .icon { font-size: 3rem; margin-bottom: 12px; }
    .empty-state h3 { color: #94A3B8; font-size: 1.1rem; margin-bottom: 8px; }
    .empty-state p  { font-size: 0.88rem; }

    /* ---------- wizard step indicator ---------- */
    .wizard-steps {
        display: flex;
        gap: 8px;
        margin-bottom: 18px;
        align-items: center;
    }
    .wstep {
        padding: 4px 14px;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .wstep-active  { background: #3B82F6; color: #fff; }
    .wstep-done    { background: #22C55E22; color: #22C55E; border: 1px solid #22C55E55; }
    .wstep-pending { background: #1E293B;   color: #64748B; border: 1px solid #334155; }

    /* ---------- makefile commands ---------- */
    .cmd-block {
        background: #0D1B2A;
        border: 1px solid #1E293B;
        border-radius: 8px;
        padding: 10px 14px;
        font-family: monospace;
        font-size: 0.78rem;
        color: #94A3B8;
    }
    .cmd-block .cmd-name { color: #3B82F6; font-weight: 600; }
    .cmd-block .cmd-comment { color: #475569; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Session state init
# ---------------------------------------------------------------------------

def _init_state():
    defaults = {
        # legacy keys (kept for safety — sidebar niche selector may still reference them)
        "wizard_step": 1,
        "wizard_name": "",
        "wizard_mode": "content",
        "wizard_suggested_kws": [],
        "wizard_selected_kws": set(),
        "wizard_manual_kws": [],
        "wizard_custom_input": "",
        # new wizard keys
        "wiz_step": 0,
        "wiz_category": "",
        "wiz_suggested_niches": [],
        "wiz_selected_niche": {},
        "wiz_suggested_keywords": [],
        "wiz_checked_keywords": [],
        "wiz_extra_keywords": [],
        "wiz_mode": "content",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()

# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------


def _get(path: str) -> dict | list | None:
    try:
        r = httpx.get(f"{API_BASE}{path}", timeout=8)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _post(path: str, body: dict) -> tuple[dict | None, int | None]:
    """Returns (data, status_code). data is None on error."""
    try:
        r = httpx.post(f"{API_BASE}{path}", json=body, timeout=15)
        if r.status_code in (200, 201, 202):
            try:
                return r.json(), r.status_code
            except Exception:
                return {}, r.status_code
        return None, r.status_code
    except Exception:
        return None, None


def _delete(path: str) -> bool:
    try:
        r = httpx.delete(f"{API_BASE}{path}", timeout=8)
        return r.status_code == 204
    except Exception:
        return False


@st.cache_data(ttl=60)
def fetch_health() -> dict | None:
    return _get("/health")


@st.cache_data(ttl=60)
def fetch_niches() -> list:
    result = _get("/niches")
    return result if result is not None else []


@st.cache_data(ttl=60)
def fetch_content_briefing(niche_id: int) -> dict | None:
    return _get(f"/briefing/{niche_id}")


@st.cache_data(ttl=60)
def fetch_product_briefing(niche_id: int) -> dict | None:
    return _get(f"/product-briefing/{niche_id}")


@st.cache_data(ttl=60)
def fetch_opportunities(niche_id: int) -> list:
    result = _get(f"/opportunities?niche_id={niche_id}")
    return result if result is not None else []


# ---------------------------------------------------------------------------
# Render helpers
# ---------------------------------------------------------------------------


def badge(text: str, color: str) -> str:
    return f'<span class="badge" style="background:{color}">{text}</span>'


def badge_manual(text: str) -> str:
    return f'<span class="badge badge-manual">{text}</span>'


def score_bar(value: float, max_val: float = 10.0, color: str | None = None) -> str:
    pct = min(100, max(0, (value / max_val) * 100))
    fill_color = color or PALETTE["primary"]
    return (
        f'<div class="score-bar-wrap">'
        f'<div class="score-bar-fill" style="width:{pct:.1f}%;background:{fill_color}"></div>'
        f"</div>"
    )


def section_header(title: str, subtitle: str = ""):
    st.markdown(
        f'<div class="section-header"><h2>{title}</h2></div>'
        + (f'<p class="section-subtitle">{subtitle}</p>' if subtitle else ""),
        unsafe_allow_html=True,
    )


def empty_state(icon: str, title: str, desc: str = ""):
    st.markdown(
        f'<div class="empty-state">'
        f'<div class="icon">{icon}</div>'
        f"<h3>{title}</h3>"
        + (f"<p>{desc}</p>" if desc else "")
        + "</div>",
        unsafe_allow_html=True,
    )


def run_pipeline_button(niche_id: int, mode: str, key_suffix: str = ""):
    btn_key = f"run_pipeline_{niche_id}_{mode}_{key_suffix}"
    if st.button(f"▶ Correr pipeline ahora", key=btn_key, type="primary", use_container_width=True):
        with st.spinner("Iniciando pipeline…"):
            data, status = _post(f"/pipeline/run/{niche_id}", {"mode": mode})
        if data is not None:
            st.success("Pipeline iniciado en background. Refrescá en ~2 minutos.")
            st.cache_data.clear()
        else:
            st.error(f"No se pudo iniciar el pipeline (status={status}). Verificá el backend.")


# ---------------------------------------------------------------------------
# Wizard — crear nicho (4 pasos basados en categorías)
# ---------------------------------------------------------------------------

_WIZ_CATEGORIES = [
    "🛠 Dev Tools",
    "📚 Educación",
    "💰 Finanzas personales",
    "✍️ Creación de contenido",
    "🤖 IA / Automatización",
    "🛒 E-commerce",
    "🎯 Marketing digital",
    "📱 No-Code / Low-Code",
    "💼 SaaS B2B",
]

_WIZ_MODE_OPTIONS = {
    "content": "📝 Content — encontrá sobre qué escribir",
    "product": "📦 Product — encontrá qué producto construir",
    "both": "🚀 Both — los dos análisis juntos",
}


def _wiz_reset():
    """Resetea todo el wizard al paso 0."""
    keys = [
        "wiz_step", "wiz_category", "wiz_suggested_niches", "wiz_selected_niche",
        "wiz_suggested_keywords", "wiz_checked_keywords", "wiz_extra_keywords", "wiz_mode",
    ]
    for k in keys:
        if k in st.session_state:
            del st.session_state[k]
    _init_state()


def _wiz_step_indicator(current: int):
    steps = ["Categoría", "Nicho", "Keywords", "Crear"]
    parts = []
    for i, label in enumerate(steps):
        if i < current:
            parts.append(f'<span class="wstep wstep-done">✓ {label}</span>')
        elif i == current:
            parts.append(f'<span class="wstep wstep-active">{label}</span>')
        else:
            parts.append(f'<span class="wstep wstep-pending">{label}</span>')
    st.markdown(
        '<div class="wizard-steps">' + "".join(parts) + "</div>",
        unsafe_allow_html=True,
    )


def _wiz_step0():
    """Paso 0 — Grilla de categorías."""
    _wiz_step_indicator(0)
    st.markdown("**¿En qué área querés encontrar oportunidades?**")

    rows = [_WIZ_CATEGORIES[i : i + 3] for i in range(0, len(_WIZ_CATEGORIES), 3)]
    for row in rows:
        cols = st.columns(3)
        for col, cat in zip(cols, row):
            with col:
                if st.button(cat, use_container_width=True, key=f"wiz_cat_{cat}"):
                    st.session_state.wiz_category = cat
                    with st.spinner("Claude está analizando oportunidades..."):
                        data, _ = _post("/niches/suggest", {"category": cat})
                    niches = data.get("niches", []) if data else []
                    st.session_state.wiz_suggested_niches = niches
                    st.session_state.wiz_step = 1
                    st.rerun()


def _wiz_step1():
    """Paso 1 — Cards de nichos sugeridos."""
    _wiz_step_indicator(1)
    category = st.session_state.wiz_category
    st.markdown(f"**Nichos rentables en {category}**")

    niches = st.session_state.wiz_suggested_niches
    if not niches:
        st.warning("No se obtuvieron sugerencias. Volvé e intentá de nuevo.")
    else:
        rows = [niches[i : i + 3] for i in range(0, len(niches), 3)]
        for row in rows:
            cols = st.columns(3)
            for col, niche in zip(cols, row):
                with col:
                    name = niche.get("name", "")
                    description = niche.get("description", "")
                    why_profitable = niche.get("why_profitable", "")
                    st.markdown(
                        f'<div class="card card-hover" style="margin-bottom:8px;min-height:130px">'
                        f'<p style="margin:0 0 4px;font-weight:700">{name}</p>'
                        f'<p style="margin:0 0 6px;color:#94A3B8;font-size:0.83rem">{description}</p>'
                        f'<p style="margin:0;font-style:italic;color:#64748B;font-size:0.8rem">💡 {why_profitable}</p>'
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        "Elegir este nicho →",
                        key=f"wiz_pick_{name}",
                        use_container_width=True,
                    ):
                        st.session_state.wiz_selected_niche = {"name": name, "description": description}
                        with st.spinner("Consultando keywords con IA…"):
                            kw_data, _ = _post("/keywords/suggest", {"niche_name": name})
                        keywords = kw_data.get("keywords", []) if kw_data else []
                        st.session_state.wiz_suggested_keywords = keywords
                        st.session_state.wiz_checked_keywords = list(keywords)
                        st.session_state.wiz_extra_keywords = []
                        st.session_state.wiz_step = 2
                        st.rerun()

    st.markdown(" ")
    if st.button("← Volver", key="wiz_back_1", use_container_width=False):
        st.session_state.wiz_step = 0
        st.rerun()


def _wiz_step2():
    """Paso 2 — Selección de keywords."""
    _wiz_step_indicator(2)
    niche_name = st.session_state.wiz_selected_niche.get("name", "")
    st.markdown(f"**Keywords para {niche_name}**")

    suggested = st.session_state.wiz_suggested_keywords
    checked = list(st.session_state.wiz_checked_keywords)
    extra = list(st.session_state.wiz_extra_keywords)

    # Checkboxes en 3 columnas — todas marcadas por default
    if suggested:
        st.caption("Seleccioná las keywords que apliquen:")
        cols = st.columns(3)
        new_checked: list[str] = []
        for i, kw in enumerate(suggested):
            with cols[i % 3]:
                is_checked = st.checkbox(kw, value=(kw in checked), key=f"wiz_kw_{i}")
                if is_checked:
                    new_checked.append(kw)
        st.session_state.wiz_checked_keywords = new_checked

    # Input manual
    st.markdown("---")
    col_input, col_add = st.columns([4, 1])
    with col_input:
        custom = st.text_input(
            "Keyword propia",
            placeholder="ej: automation tools, no-code workflows…",
            label_visibility="collapsed",
            key="wiz_custom_kw_input",
        )
    with col_add:
        if st.button("＋ Agregar", use_container_width=True, key="wiz_add_kw"):
            kw = custom.strip()
            if kw and kw not in extra:
                extra.append(kw)
                st.session_state.wiz_extra_keywords = extra
                st.rerun()

    if extra:
        st.markdown("*Agregadas manualmente:*")
        st.markdown(" ".join(badge_manual(kw) for kw in extra), unsafe_allow_html=True)

    # Discovery mode
    st.markdown(" ")
    mode = st.selectbox(
        "Discovery mode",
        options=list(_WIZ_MODE_OPTIONS.keys()),
        format_func=lambda x: _WIZ_MODE_OPTIONS[x],
        index=list(_WIZ_MODE_OPTIONS.keys()).index(st.session_state.wiz_mode),
        key="wiz_mode_select",
    )
    st.session_state.wiz_mode = mode

    st.markdown(" ")
    col_back, col_next = st.columns(2)
    with col_back:
        if st.button("← Volver", use_container_width=True, key="wiz_back_2"):
            st.session_state.wiz_step = 1
            st.rerun()
    with col_next:
        all_kws = list(st.session_state.wiz_checked_keywords) + extra
        if st.button("Confirmar y crear →", type="primary", use_container_width=True, key="wiz_confirm"):
            if not all_kws:
                st.warning("Seleccioná o agregá al menos una keyword.")
            else:
                st.session_state.wiz_extra_keywords = extra
                _wiz_step3_create(niche_name, all_kws, mode)


def _wiz_step3_create(niche_name: str, all_kws: list[str], mode: str):
    """Paso 3 — Creación y éxito (se ejecuta inline desde paso 2 al confirmar)."""
    payload = {
        "name": niche_name,
        "keywords": all_kws,
        "discovery_mode": mode,
    }
    data, status = _post("/niches", payload)
    if data is not None:
        st.success(f"Nicho «{niche_name}» creado correctamente.")
        st.balloons()
        _wiz_reset()
        st.cache_data.clear()
        st.rerun()
    else:
        st.error(f"Error al crear el nicho (status={status}). Verificá el backend.")


def render_create_niche_wizard():
    step = st.session_state.wiz_step
    if step == 0:
        _wiz_step0()
    elif step == 1:
        _wiz_step1()
    elif step == 2:
        _wiz_step2()


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------


def render_sidebar() -> tuple[str, int | None]:
    with st.sidebar:
        st.markdown(
            '<div style="font-size:2.2rem;text-align:center;padding:8px 0 4px">📡</div>'
            '<div style="font-size:1.1rem;font-weight:700;text-align:center;letter-spacing:0.04em;margin-bottom:4px">Opportunity Radar</div>',
            unsafe_allow_html=True,
        )

        # Health status
        health = fetch_health()
        if health is None:
            st.error("⚠️ Backend no disponible")
            st.stop()

        scheduler_status = health.get("scheduler", "stopped")
        if scheduler_status == "running":
            st.success("⚡ Scheduler activo")
        else:
            st.warning("⏸ Scheduler detenido")

        st.markdown("---")

        # Navigation
        section = st.radio(
            "Sección",
            options=["Nichos", "Content Briefing", "Product Briefing", "Oportunidades Raw"],
            label_visibility="collapsed",
        )

        st.markdown("---")

        # Global niche selector
        niches = fetch_niches()
        selected_niche_id: int | None = None

        if niches:
            niche_map = {n["name"]: n["id"] for n in niches}
            selected_name = st.selectbox(
                "Nicho activo",
                options=list(niche_map.keys()),
                help="Seleccioná el nicho para analizar en las secciones de briefing",
            )
            selected_niche_id = niche_map[selected_name]
        else:
            st.info("No hay nichos. Creá uno abajo.")

        st.markdown("---")

        # Useful commands expander
        with st.expander("⌨️ Comandos útiles", expanded=False):
            st.code(
                "make dev      # backend\nmake dash     # dashboard\nmake test     # tests",
                language="bash",
            )

    return section, selected_niche_id


# ---------------------------------------------------------------------------
# Section 1 — Nichos
# ---------------------------------------------------------------------------


def render_nichos():
    section_header(
        "Nichos",
        "Gestioná tus nichos de mercado y corré el pipeline de análisis.",
    )

    # --- Wizard de creación ---
    with st.expander("➕ Crear nuevo nicho", expanded=st.session_state.wiz_step > 0):
        render_create_niche_wizard()

    st.markdown("---")

    niches = fetch_niches()

    if not niches:
        empty_state(
            "🗂️",
            "No hay nichos todavía",
            "Usá el panel de arriba para crear tu primer nicho.",
        )
        return

    # Table header
    col_name, col_keywords, col_mode, col_active, col_last, col_actions = st.columns(
        [2, 3, 1.2, 1, 2, 1.8]
    )
    for col, label in zip(
        [col_name, col_keywords, col_mode, col_active, col_last, col_actions],
        ["Nombre", "Keywords", "Modo", "Estado", "Último briefing", "Acciones"],
    ):
        with col:
            st.markdown(f"<small style='color:#64748B;font-weight:600'>{label}</small>", unsafe_allow_html=True)

    st.markdown("<hr style='margin:6px 0 10px;border-color:#263348'>", unsafe_allow_html=True)

    for niche in niches:
        nid = niche["id"]
        col_name, col_keywords, col_mode, col_active, col_last, col_actions = st.columns(
            [2, 3, 1.2, 1, 2, 1.8]
        )

        with col_name:
            st.markdown(f"**{niche['name']}**")

        with col_keywords:
            kws = niche.get("keywords", [])
            tags_html = " ".join(badge(k, PALETTE["surface2"]) for k in kws[:5])
            if len(kws) > 5:
                muted_color = PALETTE["muted"]
                extra = len(kws) - 5
                tags_html += f" <span style='color:{muted_color};font-size:0.75rem'>+{extra}</span>"
            st.markdown(tags_html or "<span style='color:#475569'>—</span>", unsafe_allow_html=True)

        with col_mode:
            mode = niche.get("discovery_mode", "content")
            st.markdown(badge(mode, DISCOVERY_MODE_COLORS.get(mode, PALETTE["muted"])), unsafe_allow_html=True)

        with col_active:
            if niche.get("active", True):
                st.markdown(badge("activo", PALETTE["success"]), unsafe_allow_html=True)
            else:
                st.markdown(badge("inactivo", PALETTE["muted"]), unsafe_allow_html=True)

        with col_last:
            # Try to get last briefing date
            briefing = fetch_content_briefing(nid)
            if briefing and briefing.get("generated_at"):
                raw_ts = briefing["generated_at"]
                # Show only date portion if it contains T
                ts_display = raw_ts.split("T")[0] if "T" in raw_ts else raw_ts
                st.markdown(f"<small style='color:#94A3B8'>{ts_display}</small>", unsafe_allow_html=True)
            else:
                st.markdown("<small style='color:#475569'>Sin datos</small>", unsafe_allow_html=True)

        with col_actions:
            col_run, col_del = st.columns(2)
            with col_run:
                pipeline_mode = niche.get("discovery_mode", "content")
                if st.button("▶", key=f"run_{nid}", help=f"Correr pipeline ({pipeline_mode})", use_container_width=True):
                    with st.spinner("Iniciando…"):
                        data, status = _post(f"/pipeline/run/{nid}", {"mode": pipeline_mode})
                    if data is not None:
                        st.success("Pipeline iniciado. Refrescá en ~2 min.")
                        st.cache_data.clear()
                    else:
                        st.error(f"Error (status={status})")
            with col_del:
                if st.button("🗑", key=f"del_{nid}", help="Eliminar nicho", use_container_width=True):
                    ok = _delete(f"/niches/{nid}")
                    if ok:
                        st.success(f"Nicho «{niche['name']}» eliminado.")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("No se pudo eliminar.")

        st.markdown("<hr style='margin:4px 0 8px;border-color:#1E293B'>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Section 2 — Content Briefing
# ---------------------------------------------------------------------------


def _radar_chart(opp: dict) -> go.Figure:
    score = opp.get("score", {})
    dimensions = ["trend_velocity", "competition_gap", "social_signal", "monetization_intent"]
    labels = ["Trend Velocity", "Competition Gap", "Social Signal", "Monetization Intent"]
    values = [score.get(d, 0) for d in dimensions]
    values_closed = values + [values[0]]
    labels_closed = labels + [labels[0]]

    fig = go.Figure(
        go.Scatterpolar(
            r=values_closed,
            theta=labels_closed,
            fill="toself",
            fillcolor="rgba(59,130,246,0.2)",
            line=dict(color=PALETTE["primary"], width=2),
            marker=dict(color=PALETTE["primary"], size=6),
        )
    )
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 10], tickfont=dict(size=9), gridcolor="#263348"),
            angularaxis=dict(tickfont=dict(size=11), gridcolor="#263348"),
            bgcolor="rgba(0,0,0,0)",
        ),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=40, t=40, b=40),
        height=300,
    )
    return fig


def render_content_briefing(niche_id: int | None):
    section_header(
        "Content Briefing",
        "Oportunidades de contenido detectadas por el pipeline de análisis.",
    )

    if niche_id is None:
        empty_state("👈", "Seleccioná un nicho", "Usá el selector del sidebar para elegir un nicho.")
        return

    briefing = fetch_content_briefing(niche_id)

    if briefing is None:
        st.markdown(
            '<div class="card" style="text-align:center;padding:40px 20px">'
            '<div style="font-size:2.5rem;margin-bottom:12px">⚙️</div>'
            '<h3 style="color:#94A3B8;margin:0 0 8px">El pipeline todavía no corrió para este nicho</h3>'
            '<p style="color:#64748B;font-size:0.88rem;margin:0 0 20px">Inicialo manualmente y en ~2 minutos vas a ver los resultados.</p>'
            "</div>",
            unsafe_allow_html=True,
        )
        run_pipeline_button(niche_id, "content", "briefing_top")
        return

    opportunities = briefing.get("opportunities", [])

    if not opportunities:
        st.markdown(
            '<div class="card" style="text-align:center;padding:40px 20px">'
            '<div style="font-size:2.5rem;margin-bottom:12px">📭</div>'
            '<h3 style="color:#94A3B8;margin:0 0 8px">Sin oportunidades todavía</h3>'
            '<p style="color:#64748B;font-size:0.88rem;margin:0 0 20px">El pipeline corrió pero no generó resultados. Probá correrlo de nuevo.</p>'
            "</div>",
            unsafe_allow_html=True,
        )
        run_pipeline_button(niche_id, "content", "briefing_empty")
        return

    # Top metrics (native st.metric)
    total = len(opportunities)
    avg_score = sum(o["score"]["total"] for o in opportunities) / total
    confidence_counts: dict[str, int] = {}
    for o in opportunities:
        c = o["score"].get("confidence", "medium")
        confidence_counts[c] = confidence_counts.get(c, 0) + 1
    top_confidence = max(confidence_counts, key=lambda k: confidence_counts[k])
    high_count = confidence_counts.get("high", 0)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Oportunidades", total)
    col2.metric("Score promedio", f"{avg_score:.1f} / 10")
    col3.metric("Confianza predominante", top_confidence.capitalize())
    col4.metric("Alta confianza", high_count)

    st.markdown("---")

    # Radar + top opp detail
    top_opp = opportunities[0]
    col_radar, col_info = st.columns([1, 1])

    with col_radar:
        st.subheader("🏆 Top Oportunidad — Radar")
        st.plotly_chart(_radar_chart(top_opp), use_container_width=True)

    with col_info:
        st.subheader("Detalle")
        score = top_opp["score"]
        confidence = score.get("confidence", "medium")
        st.markdown(f"**Topic:** {top_opp['topic']}")
        st.markdown(
            f"**Confianza:** {badge(confidence, CONFIDENCE_COLORS.get(confidence, PALETTE['muted']))}",
            unsafe_allow_html=True,
        )
        st.metric("Score Total", f"{score['total']:.2f} / 10")
        st.markdown("**Acción Recomendada:**")
        st.info(top_opp.get("recommended_action", "—"))

    st.markdown("---")
    st.subheader("Todas las oportunidades")

    rows = sorted(
        opportunities,
        key=lambda o: o["score"]["total"],
        reverse=True,
    )
    for opp in rows:
        s = opp["score"]
        confidence = s.get("confidence", "medium")
        c_topic, c_score, c_conf, c_action = st.columns([3, 2, 1.5, 3])

        with c_topic:
            st.markdown(f"**{opp['topic']}**")
        with c_score:
            st.markdown(
                f"{s['total']:.1f} / 10 {score_bar(s['total'])}",
                unsafe_allow_html=True,
            )
        with c_conf:
            st.markdown(
                badge(confidence, CONFIDENCE_COLORS.get(confidence, PALETTE["muted"])),
                unsafe_allow_html=True,
            )
        with c_action:
            st.markdown(
                f"<small style='color:#94A3B8'>{opp.get('recommended_action', '—')}</small>",
                unsafe_allow_html=True,
            )

    st.markdown(" ")


# ---------------------------------------------------------------------------
# Section 3 — Product Briefing
# ---------------------------------------------------------------------------


def _horizontal_bar_chart(opportunities: list) -> go.Figure:
    top5 = sorted(opportunities, key=lambda o: o["score"]["total"], reverse=True)[:5]
    labels = [o["topic"][:40] + ("…" if len(o["topic"]) > 40 else "") for o in top5]
    values = [o["score"]["total"] for o in top5]
    colors = [
        PRODUCT_TYPE_COLORS.get(o.get("product_type", ""), PALETTE["primary"]) for o in top5
    ]

    fig = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker_color=colors,
            text=[f"{v:.1f}" for v in values],
            textposition="outside",
        )
    )
    fig.update_layout(
        xaxis=dict(range=[0, 10], title="Score Total", tickfont=dict(size=10), gridcolor="#263348"),
        yaxis=dict(autorange="reversed", tickfont=dict(size=11)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=50, t=20, b=20),
        height=280,
        showlegend=False,
    )
    return fig


def render_product_briefing(niche_id: int | None):
    section_header(
        "Product Briefing",
        "Oportunidades de producto digital detectadas por el pipeline.",
    )

    if niche_id is None:
        empty_state("👈", "Seleccioná un nicho", "Usá el selector del sidebar para elegir un nicho.")
        return

    briefing = fetch_product_briefing(niche_id)

    if briefing is None:
        st.markdown(
            '<div class="card" style="text-align:center;padding:40px 20px">'
            '<div style="font-size:2.5rem;margin-bottom:12px">⚙️</div>'
            '<h3 style="color:#94A3B8;margin:0 0 8px">El pipeline todavía no corrió para este nicho</h3>'
            '<p style="color:#64748B;font-size:0.88rem;margin:0 0 20px">Inicialo manualmente y en ~2 minutos vas a ver los resultados.</p>'
            "</div>",
            unsafe_allow_html=True,
        )
        run_pipeline_button(niche_id, "product", "prod_briefing_top")
        return

    opportunities = briefing.get("opportunities", [])

    if not opportunities:
        st.markdown(
            '<div class="card" style="text-align:center;padding:40px 20px">'
            '<div style="font-size:2.5rem;margin-bottom:12px">📭</div>'
            '<h3 style="color:#94A3B8;margin:0 0 8px">Sin oportunidades todavía</h3>'
            '<p style="color:#64748B;font-size:0.88rem;margin:0 0 20px">El pipeline corrió pero no generó resultados. Probá correrlo de nuevo.</p>'
            "</div>",
            unsafe_allow_html=True,
        )
        run_pipeline_button(niche_id, "product", "prod_briefing_empty")
        return

    top5 = sorted(opportunities, key=lambda o: o["score"]["total"], reverse=True)[:5]

    # Top metrics
    avg_score = sum(o["score"]["total"] for o in opportunities) / len(opportunities)
    col1, col2, col3, _ = st.columns(4)
    col1.metric("Productos analizados", len(opportunities))
    col2.metric("Score promedio", f"{avg_score:.1f} / 10")
    col3.metric("Top score", f"{top5[0]['score']['total']:.1f} / 10")

    st.markdown("---")
    st.subheader("🏆 Top 5 Oportunidades de Producto")

    cols_per_row = 3
    for row_start in range(0, len(top5), cols_per_row):
        row_opps = top5[row_start : row_start + cols_per_row]
        cols = st.columns(cols_per_row)

        for col, opp in zip(cols, row_opps):
            with col:
                score = opp["score"]
                ptype = opp.get("product_type", "")
                ptype_color = PRODUCT_TYPE_COLORS.get(ptype, PALETTE["muted"])
                confidence = score.get("confidence", "medium")
                conf_color = CONFIDENCE_COLORS.get(confidence, PALETTE["muted"])
                topic_short = opp["topic"][:55] + ("…" if len(opp["topic"]) > 55 else "")

                st.markdown(
                    f"""
                    <div class="product-card">
                        <p style="font-weight:700;font-size:0.95rem;margin:0 0 10px;line-height:1.3">{topic_short}</p>
                        <div style="margin-bottom:10px">
                            {badge(ptype or "N/A", ptype_color)}
                            &nbsp;
                            {badge(confidence, conf_color)}
                        </div>
                        <p class="price-range">{opp.get('recommended_price_range', '—')}</p>
                        <p style="color:#64748B;font-size:0.75rem;margin:0 0 10px">Precio recomendado</p>
                        <span style="font-size:0.85rem">Score: <strong>{score['total']:.1f}/10</strong></span>
                        {score_bar(score['total'], color=ptype_color)}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                with st.expander("Ver detalle"):
                    detail_dims = [
                        ("Frustration Level", score.get("frustration_level", 0)),
                        ("Market Size", score.get("market_size", 0)),
                        ("Competition Gap", score.get("competition_gap", 0)),
                        ("Willingness to Pay", score.get("willingness_to_pay", 0)),
                    ]
                    for dim_label, dim_val in detail_dims:
                        st.markdown(
                            f"**{dim_label}:** {dim_val:.1f} {score_bar(dim_val)}",
                            unsafe_allow_html=True,
                        )
                    st.markdown("**Razonamiento:**")
                    st.markdown(
                        f"<small style='color:#94A3B8'>{opp.get('product_reasoning', '—')}</small>",
                        unsafe_allow_html=True,
                    )

    st.markdown("---")
    st.subheader("Comparativa de Score (Top 5)")
    st.plotly_chart(_horizontal_bar_chart(top5), use_container_width=True)


# ---------------------------------------------------------------------------
# Section 4 — Raw Opportunities
# ---------------------------------------------------------------------------


def render_raw_opportunities(niche_id: int | None):
    section_header(
        "Oportunidades Raw",
        "Datos crudos de oportunidades para análisis detallado.",
    )

    if niche_id is None:
        empty_state("👈", "Seleccioná un nicho", "Usá el selector del sidebar para elegir un nicho.")
        return

    opportunities = fetch_opportunities(niche_id)

    if not opportunities:
        empty_state(
            "📭",
            "Sin oportunidades para este nicho",
            "Corré el pipeline primero para generar datos.",
        )
        return

    col_filter, _ = st.columns([2, 6])
    with col_filter:
        conf_filter = st.selectbox(
            "Filtrar por confianza",
            options=["all", "high", "medium", "low"],
            format_func=lambda x: x.capitalize() if x != "all" else "Todas",
        )

    rows = []
    for opp in opportunities:
        s = opp.get("score", {})
        confidence = s.get("confidence", "medium")
        if conf_filter != "all" and confidence != conf_filter:
            continue
        rows.append(
            {
                "Topic": opp["topic"],
                "Trend Velocity": round(s.get("trend_velocity", 0), 2),
                "Competition Gap": round(s.get("competition_gap", 0), 2),
                "Social Signal": round(s.get("social_signal", 0), 2),
                "Monetization Intent": round(s.get("monetization_intent", 0), 2),
                "Total": round(s.get("total", 0), 2),
                "Confidence": confidence,
            }
        )

    if not rows:
        st.info("No hay oportunidades con ese filtro de confianza.")
        return

    df = pd.DataFrame(rows).sort_values("Total", ascending=False).reset_index(drop=True)

    def color_confidence(val: str) -> str:
        m = {"high": "#22C55E", "medium": "#F97316", "low": "#EF4444"}
        return f"color: {m.get(val, '#6B7280')}; font-weight: 600"

    def color_score(val: float) -> str:
        if val >= 7:
            return f"color: {PALETTE['success']}"
        if val >= 5:
            return f"color: {PALETTE['warning']}"
        return f"color: {PALETTE['danger']}"

    score_cols = ["Trend Velocity", "Competition Gap", "Social Signal", "Monetization Intent", "Total"]
    styled = (
        df.style
        .map(color_confidence, subset=["Confidence"])
        .map(color_score, subset=score_cols)
        .format({c: "{:.2f}" for c in score_cols})
    )

    st.dataframe(styled, use_container_width=True, hide_index=True)
    st.caption(f"{len(df)} oportunidades encontradas.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    section, selected_niche_id = render_sidebar()

    if section == "Nichos":
        render_nichos()
    elif section == "Content Briefing":
        render_content_briefing(selected_niche_id)
    elif section == "Product Briefing":
        render_product_briefing(selected_niche_id)
    elif section == "Oportunidades Raw":
        render_raw_opportunities(selected_niche_id)


if __name__ == "__main__" or True:
    main()
