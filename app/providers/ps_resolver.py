from . import online
_cache=None
def resolve_ps4(title_id):
 global _cache
 if not title_id:return None
 if _cache is None:
  try:_cache=online.ps4_catalog()
  except Exception:_cache=[]
 row=online.ps4_match(_cache,title_id,None)
 return online.pick(row,'title','name') if row else None
