from __future__ import annotations

from dataclasses import dataclass
from .identifiers import normalize_isbn

GRID_BITS=16; GRID_SIZE=1<<GRID_BITS; ISBN_MIN_BODY=978_000_000_000; ISBN_MAX_BODY=979_999_999_999; HILBERT_MAX=GRID_SIZE*GRID_SIZE-1

@dataclass(frozen=True, slots=True)
class SpacePoint:
    isbn13:str; x:float; y:float; grid_x:int; grid_y:int
    def to_dict(self): return {"isbn13":self.isbn13,"x":self.x,"y":self.y,"grid_x":self.grid_x,"grid_y":self.grid_y}

def _rot(n,x,y,rx,ry):
    if ry==0:
        if rx==1: x=n-1-x; y=n-1-y
        x,y=y,x
    return x,y

def hilbert_d_to_xy(size:int,distance:int)->tuple[int,int]:
    if size<=0 or size&(size-1): raise ValueError("size must be a positive power of two")
    if not 0<=distance<size*size: raise ValueError("distance outside Hilbert square")
    x=y=0; t=distance; s=1
    while s<size:
        rx=1&(t//2); ry=1&(t^rx); x,y=_rot(s,x,y,rx,ry); x+=s*rx; y+=s*ry; t//=4; s*=2
    return x,y

def isbn_space_point(isbn:str)->SpacePoint:
    isbn13=normalize_isbn(isbn); body=int(isbn13[:12])
    if not ISBN_MIN_BODY<=body<=ISBN_MAX_BODY: raise ValueError("ISBN prefix is outside the 978/979 namespace")
    span=ISBN_MAX_BODY-ISBN_MIN_BODY; offset=body-ISBN_MIN_BODY; distance=round(offset*HILBERT_MAX/span); gx,gy=hilbert_d_to_xy(GRID_SIZE,distance); denom=GRID_SIZE-1
    return SpacePoint(isbn13,gx/denom,gy/denom,gx,gy)

def space_metadata()->dict[str,object]:
    return {"name":"Cyber Library ISBN Hilbert Space","version":1,"algorithm":"scaled ISBN-13 body -> order-16 Hilbert curve","grid_size":GRID_SIZE,"isbn_prefixes":["978","979"],"independent_implementation":True}
