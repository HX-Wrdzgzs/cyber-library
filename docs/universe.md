# ISBN Universe

The ISBN Universe is a visual coordinate layer over ISBN-13.

## Why an independent coordinate system?

`phiresky/isbn-visualization` inspired the product idea, but Cyber Library avoids
copying its AGPL source into the MIT project.

Instead, Cyber Library uses a clean-room mapping:

1. validate ISBN-13;
2. remove the checksum digit;
3. map the 978/979 namespace to a continuous integer offset;
4. scale the offset across an order-16 Hilbert curve;
5. expose normalized x/y coordinates in `[0, 1]`.

The grid contains `65,536 × 65,536` possible cells.

## Properties

- deterministic;
- stable across machines;
- adjacent ISBN offsets tend to retain spatial locality;
- independent of subject classification.

The last point matters: ISBN registration space is not a content taxonomy.

## API

```text
GET /api/universe
  ?min_x=0
  &max_x=1
  &min_y=0
  &max_y=1
  &limit=2500
  &category=Computer%20Science
  &q=machine%20learning
```

For a catalog containing tens of millions of editions, v1.1 should replace
point-level responses at low zoom with precomputed density tiles/clusters.
