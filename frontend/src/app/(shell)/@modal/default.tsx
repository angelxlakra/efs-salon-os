// Parallel slot default. When no @modal route matches, render nothing.
// (Required by Next.js: a parallel slot must always have a `default.tsx` so
// route changes outside the slot don't unmount it.)
export default function ModalDefault() {
  return null;
}
