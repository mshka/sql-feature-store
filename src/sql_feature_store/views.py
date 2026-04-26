from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class FeatureView:
    """Declarative description of a set of features keyed by an entity column.

    Pure metadata — no engine, no SQL, no registry. The library uses this to
    drive entity-keyed reads (`FeatureStore.get_online_features`) and freshness
    queries (`FeatureStore.last_updated`); raw SQL via `FeatureStore.read`
    stays view-unaware.

    Per-feature metadata (dtype, nullable, description) intentionally lives in
    the SQL schema, not here. Callers who want typed returns pass a `dtype=`
    kwarg to `get_online_features`, same shape as `pd.read_sql`'s `dtype`.
    """

    table: str
    entity: str
    features: List[str]
    last_updated: Optional[str] = None
