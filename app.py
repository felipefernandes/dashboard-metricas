from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd
import plotly.express as px
import streamlit as st


CSV_DEFAULT_PATH = Path("JIRA.csv")

COL_ISSUE_TYPE = "Issue Type"
COL_CREATED = "Created"
COL_START = "Custom field (Start Progress)"
COL_CLOSE = "Custom field (Close Progress)"


@dataclass(frozen=True)
class ParsedData:
    raw: pd.DataFrame
    flow: pd.DataFrame  # itens com Start e Close válidos + cycle_time


def _parse_jira_datetime(series: pd.Series) -> pd.Series:
    """
    Ex.: '22/Dec/25 12:00 AM' (CSV do Jira geralmente vem assim)
    """
    return pd.to_datetime(series, format="%d/%b/%y %I:%M %p", errors="coerce")


def load_data_from_csv(file) -> pd.DataFrame:
    df = pd.read_csv(file)

    # Normaliza Issue Type (para evitar 'Bug' vs 'bug' etc.)
    df[COL_ISSUE_TYPE] = df[COL_ISSUE_TYPE].astype(str).str.strip()

    # Parse de datas
    df[COL_CREATED] = _parse_jira_datetime(df.get(COL_CREATED))
    df[COL_START] = _parse_jira_datetime(df.get(COL_START))
    df[COL_CLOSE] = _parse_jira_datetime(df.get(COL_CLOSE))

    return df


def build_flow_df(df: pd.DataFrame) -> ParsedData:
    flow = df.copy()

    # Mantém somente itens com Start e Close válidos (definição do seu período)
    flow = flow.dropna(subset=[COL_START, COL_CLOSE]).copy()

    # Cycle Time em dias (mínimo 1 dia, inclusive quando Start == Close)
    cycle_days = (flow[COL_CLOSE] - flow[COL_START]).dt.total_seconds() / 86400.0
    flow["cycle_time_days"] = cycle_days.clip(lower=0).apply(lambda x: max(int(round(x)), 1))

    return ParsedData(raw=df, flow=flow)


def filter_date_range(
    flow_df: pd.DataFrame,
    raw_df: pd.DataFrame,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    - Flow metrics: filtra por Close Progress no range (itens concluídos no período)
    - Bugs criados: filtra por Created no range
    """
    end_exclusive = end_date + pd.Timedelta(days=1)

    flow_in_range = flow_df[
        (flow_df[COL_CLOSE] >= start_date) & (flow_df[COL_CLOSE] < end_exclusive)
    ].copy()

    raw_in_range_created = raw_df[
        (raw_df[COL_CREATED] >= start_date) & (raw_df[COL_CREATED] < end_exclusive)
    ].copy()

    return flow_in_range, raw_in_range_created


def count_types(df: pd.DataFrame) -> dict:
    s = df[COL_ISSUE_TYPE].astype(str).str.strip().str.lower()
    return {
        "story": int((s == "story").sum()),
        "task": int((s == "task").sum()),
        "bug": int((s == "bug").sum()),
    }


def compute_metrics(flow_in_range: pd.DataFrame, raw_created_in_range: pd.DataFrame, start_date, end_date) -> dict:
    # Contagens (Story/Task/Bug) no fluxo concluído no período
    types_flow = count_types(flow_in_range)

    # Bugs criados no período (conforme sua definição)
    types_created = count_types(raw_created_in_range)
    bugs_created = types_created["bug"]

    # Throughput médio dentro do range (itens concluídos / duração)
    days = max((end_date - start_date).days + 1, 1)
    completed_total = len(flow_in_range)
    tp_per_day = completed_total / days
    tp_per_week = tp_per_day * 7

    # Cycle time médio
    ct_avg = float(flow_in_range["cycle_time_days"].mean()) if completed_total > 0 else 0.0

    # Densidade de defeitos = (Stories + Tasks) / Bugs criados
    numerator = types_flow["story"] + types_flow["task"]
    defect_density = (numerator / bugs_created) if bugs_created > 0 else None

    return {
        "days_in_range": days,
        "completed_total": completed_total,
        "tp_per_day": tp_per_day,
        "tp_per_week": tp_per_week,
        "ct_avg_days": ct_avg,
        "stories_done": types_flow["story"],
        "tasks_done": types_flow["task"],
        "bugs_done": types_flow["bug"],
        "bugs_created": bugs_created,
        "defect_density": defect_density,
    }


def chart_throughput_weekly(flow_in_range: pd.DataFrame) -> Optional[px.line]:
    if flow_in_range.empty:
        return None
    tmp = flow_in_range.copy()
    tmp["week"] = tmp[COL_CLOSE].dt.to_period("W").dt.start_time
    weekly = tmp.groupby("week").size().reset_index(name="completed")
    return px.line(weekly, x="week", y="completed", markers=True, title="Throughput por semana (concluídos)")


def chart_cycle_time_hist(flow_in_range: pd.DataFrame) -> Optional[px.histogram]:
    if flow_in_range.empty:
        return None
    return px.histogram(
        flow_in_range,
        x="cycle_time_days",
        nbins=20,
        title="Distribuição do Cycle Time (dias)",
    )


def main():
    st.set_page_config(page_title="JIRA Flow Dashboard", layout="wide")
    st.title("📊 JIRA Flow Dashboard (CSV)")

    with st.sidebar:
        st.subheader("Fonte de dados")
        uploaded = st.file_uploader("Upload do CSV do Jira", type=["csv"])
        use_default = st.checkbox("Usar JIRA.csv da pasta do projeto", value=(uploaded is None))

        if uploaded is None and use_default:
            if not CSV_DEFAULT_PATH.exists():
                st.error("Não achei o arquivo JIRA.csv na pasta do projeto. Faça upload ou coloque o arquivo ao lado do app.py.")
                st.stop()
            file = CSV_DEFAULT_PATH
        elif uploaded is not None:
            file = uploaded
        else:
            st.stop()

    df = load_data_from_csv(file)
    parsed = build_flow_df(df)

    # Range default baseado nos dados disponíveis
    min_close = parsed.flow[COL_CLOSE].min()
    max_close = parsed.flow[COL_CLOSE].max()

    if pd.isna(min_close) or pd.isna(max_close):
        st.error("Não encontrei itens com Start Progress e Close Progress válidos para calcular fluxo.")
        st.stop()

    with st.sidebar:
        st.subheader("Filtros")
        start = st.date_input("Data inicial (Close Progress)", value=min_close.date())
        end = st.date_input("Data final (Close Progress)", value=max_close.date())

    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)

    flow_in_range, raw_created_in_range = filter_date_range(parsed.flow, parsed.raw, start_ts, end_ts)
    metrics = compute_metrics(flow_in_range, raw_created_in_range, start_ts, end_ts)

    # ====== KPIs ======
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Itens concluídos", f"{metrics['completed_total']}")
    c2.metric("Throughput médio (itens/dia)", f"{metrics['tp_per_day']:.2f}")
    c3.metric("Throughput médio (itens/semana)", f"{metrics['tp_per_week']:.2f}")
    c4.metric("Cycle Time médio (dias)", f"{metrics['ct_avg_days']:.2f}")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Stories concluídas", f"{metrics['stories_done']}")
    c6.metric("Tasks concluídas", f"{metrics['tasks_done']}")
    c7.metric("Bugs concluídos", f"{metrics['bugs_done']}")
    c8.metric("Bugs criados (no range)", f"{metrics['bugs_created']}")

    st.divider()

    # Defect density
    dd = metrics["defect_density"]
    if dd is None:
        st.warning("Densidade de defeitos: sem Bugs criados no range (divisão por zero).")
    else:
        st.info(f"**Densidade de defeitos** = (Stories + Tasks) / Bugs criados = **{dd:.2f}**")

    # ====== Charts ======
    left, right = st.columns(2)
    with left:
        fig_tp = chart_throughput_weekly(flow_in_range)
        if fig_tp:
            st.plotly_chart(fig_tp, use_container_width=True)
        else:
            st.caption("Sem dados para gráfico de Throughput.")

    with right:
        fig_ct = chart_cycle_time_hist(flow_in_range)
        if fig_ct:
            st.plotly_chart(fig_ct, use_container_width=True)
        else:
            st.caption("Sem dados para gráfico de Cycle Time.")

    st.divider()

    # ====== Tabela detalhada (opcional) ======
    with st.expander("Ver tabela (itens concluídos no range)"):
        cols_show = [
            "Issue key",
            "Summary",
            COL_ISSUE_TYPE,
            COL_START,
            COL_CLOSE,
            "cycle_time_days",
            "Status",
            "Project name",
        ]
        existing = [c for c in cols_show if c in flow_in_range.columns]
        st.dataframe(flow_in_range[existing].sort_values(by=COL_CLOSE, ascending=False), use_container_width=True)


if __name__ == "__main__":
    main()
