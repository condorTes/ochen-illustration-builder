"""Deterministic composition with a common scale and bounded overlaps."""
import math


def clustered_positions(dimensions, width, height):
    """Arrange a main anchor with satellites; fit their entire union to the canvas.

    No object is independently resized or distorted. For large collections,
    use staggered rows, keeping the editor useful beyond editorial scenes.
    """
    count = len(dimensions)
    if count == 1:
        raw = [(0, 0)]
    elif count <= 5:
        # Each point is relative to the first object's center and source size.
        w, h = dimensions[0]
        if width >= height:
            offsets = [(0, 0), (.86, -.28), (-.55, -.67), (.63, .67), (-.7, .57)]
        else:
            offsets = [(0, 0), (.48, -.82), (-.47, .85), (-.58, -.68), (.54, .72)]
        raw = [(ox*w-dw/2, oy*h-dh/2)
               for (dw,dh),(ox,oy) in zip(dimensions, offsets)]
    else:
        cols = max(2, math.ceil(math.sqrt(count*width/height)))
        mw = max(w for w,h in dimensions)
        mh = max(h for w,h in dimensions)
        raw = [((i%cols)*mw*.95+(i//cols%2)*mw*.15,(i//cols)*mh*.95)
               for i in range(count)]
    min_x=min(x for x,y in raw); min_y=min(y for x,y in raw)
    max_x=max(x+w for (x,y),(w,h) in zip(raw,dimensions))
    max_y=max(y+h for (x,y),(w,h) in zip(raw,dimensions))
    scale=min(width*.88/(max_x-min_x),height*.84/(max_y-min_y))
    dx=(width-(max_x-min_x)*scale)/2
    dy=(height-(max_y-min_y)*scale)/2
    return scale,[((x-min_x)*scale+dx,(y-min_y)*scale+dy) for x,y in raw]
