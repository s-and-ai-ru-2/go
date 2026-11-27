# Simple Linked List: canonical case rationale

The Go reference uses a singly linked list with `top` pointing to the newest element. `Push` inserts at `top`, and `Pop` removes from `top` (LIFO stack behavior). `Array` obtains values by walking from `top` and then reverses that slice, so its public result is in insertion order (FIFO). The selected exclusions below are intentional and do not indicate a defect in the reference implementation.

| UUID | Canonical case | Decision and Go behavior |
|---|---|---|
| `70d747a1-2e84-4ebc-bc3f-dcbee6a05f6b` | `push -> Can push to an empty list` | Excluded because `f3197f0a-1fea-45a5-939f-4a5ea60387ec` reimplements the same case. `Push` sets the new node as `top`; on an empty list its `next` is `nil`, so the replacement covers the behavior. |
| `b97d00b6-2fab-435d-ae74-3233dcc13698` | `toList LIFO -> Empty linked list to list is empty` | Excluded as part of the alternative LIFO `Array` family. For an empty list, `Array` returns an empty slice; FIFO and LIFO ordering are indistinguishable in this case. |
| `eedeb95f-b5cf-431d-8ad6-5854ba6b251c` | `toList LIFO -> To list with multiple values` | Excluded because it expects LIFO output from `Array`. The Go reference walks from `top` (newest first) in `values`, then calls `slices.Reverse` in `Array`, producing FIFO/insertion order instead. |

The other excluded entries are intentionally unchanged by this task. The canonical descriptions, `reimplements` relationships, and inclusion settings are preserved. Run `python3 work/R63-T021/check.py` from the repository root to validate the metadata and execute the reference-backed exercise tests in a temporary scratch module.
