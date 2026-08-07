# DCIM Core Platform

This context defines the language used to describe Development runtime and
capability boundaries in DCIM Core Platform.

## Language

**Runtime Plane**:
A security and data boundary with an independent lifecycle and promotion path.
_Avoid_: Environment profile, Compose profile, deployment profile

**Capability Profile**:
A selectable group of platform capabilities within one Runtime Plane. It is not
a security or data-isolation boundary.
_Avoid_: Runtime Plane, security boundary
