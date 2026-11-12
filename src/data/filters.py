from dataclasses import dataclass
import pandas as pd

def _col(columns, names):
    return next((n for n in names if n in columns), None)

def _values(df, col):
    if not col: return []
    vals = df[col].dropna().unique().tolist()
    try: return sorted(vals)
    except TypeError: return sorted(vals, key=str)

@dataclass(frozen=True)
class FilterState:
    payloads: tuple = ()
    altitudes: tuple = ()
    speeds: tuple = ()
    hide_flagged: bool = False
    include_other_routes: bool = True

    @classmethod
    def from_dataframe(cls, df):
        return cls(tuple(_values(df, _col(df.columns, ('payload','payload_g','Payload')))),
                   tuple(_values(df, _col(df.columns, ('target_altitude','altitude','altitude_m','Altitude')))),
                   tuple(_values(df, _col(df.columns, ('target_speed','speed','speed_ms','Speed')))))
    @property
    def payload_options(self): return list(self.payloads)
    @property
    def altitude_options(self): return list(self.altitudes)
    @property
    def speed_options(self): return list(self.speeds)

def apply_filters(df, state):
    out = df.copy()
    specs = [
        (('payload','payload_g','Payload'), state.payloads),
        (('target_altitude','altitude','altitude_m','Altitude'), state.altitudes),
        (('target_speed','speed','speed_ms','Speed'), state.speeds),
    ]
    for aliases, selected in specs:
        col = _col(out.columns, aliases)
        if col and selected: out = out[out[col].isin(selected)]
    route = _col(out.columns, ('route','route_id','Route'))
    if route and not state.include_other_routes: out = out[out[route].astype(str).str.upper().eq('R1')]
    flag = _col(out.columns, ('flagged','is_flagged','data_flagged'))
    if flag and state.hide_flagged:
        vals = out[flag]
        out = out[~vals] if vals.dtype == bool else out[~vals.astype(str).str.lower().isin(('1','true','yes','flagged'))]
    return out.reset_index(drop=True)
